package com.example.catmonitoring

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.Bundle
import android.util.Log
import android.util.Size
import android.widget.EditText
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    private lateinit var cameraExecutor: ExecutorService
    private val client = OkHttpClient()
    private lateinit var ipInput: EditText
    private lateinit var viewFinder: PreviewView

    // Nowe: Obiekt do sterowania zoomem i latarką
    private var cameraControl: CameraControl? = null
    private var isPollerRunning = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        ipInput = findViewById(R.id.ipInput)
        viewFinder = findViewById(R.id.viewFinder)

        cameraExecutor = Executors.newFixedThreadPool(2) // Zwiększamy do 2, by jeden wątek obsługiwał poller

        if (allPermissionsGranted()) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 10)
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(viewFinder.surfaceProvider)
            }

            val imageAnalyzer = ImageAnalysis.Builder()
                .setTargetResolution(Size(640, 480))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setTargetRotation(viewFinder.display.rotation)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor) { imageProxy ->
                        processCameraFrame(imageProxy)
                    }
                }

            try {
                cameraProvider.unbindAll()
                // Nowe: Pobieramy obiekt camera, aby uzyskać dostęp do cameraControl
                val camera = cameraProvider.bindToLifecycle(
                    this,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    preview,
                    imageAnalyzer
                )
                cameraControl = camera.cameraControl

                // Uruchamiamy sprawdzanie ustawień
                if (!isPollerRunning) {
                    startSettingsPoller()
                }

            } catch (e: Exception) {
                Log.e("CAMERA", "Błąd powiązania kamery: ${e.message}")
            }

        }, ContextCompat.getMainExecutor(this))
    }

    // Nowe: Funkcja co sekundę pyta serwer o zoom i latarkę
    private fun startSettingsPoller() {
        isPollerRunning = true
        cameraExecutor.execute {
            while (isPollerRunning) {
                val serverIp = ipInput.text.toString().trim()
                if (serverIp.isNotEmpty()) {
                    val request = Request.Builder()
                        .url("http://$serverIp:5000/settings")
                        .build()

                    try {
                        client.newCall(request).execute().use { response ->
                            if (response.isSuccessful) {
                                val body = response.body?.string()
                                if (body != null) {
                                    val json = JSONObject(body)
                                    val zoom = json.getDouble("zoom").toFloat()
                                    val torch = json.getBoolean("flashlight")

                                    // Aplikujemy ustawienia na wątku głównym UI
                                    runOnUiThread {
                                        cameraControl?.setZoomRatio(zoom)
                                        cameraControl?.enableTorch(torch)
                                    }
                                }
                            }
                        }
                    } catch (e: Exception) {
                        Log.e("POLLER", "Błąd pobierania ustawień: ${e.message}")
                    }
                }
                Thread.sleep(1000) // Sprawdzaj co 1 sekundę
            }
        }
    }

    private fun processCameraFrame(image: ImageProxy) {
        val serverIp = ipInput.text.toString().trim()
        if (serverIp.isEmpty()) {
            image.close()
            return
        }

        try {
            val bitmap = image.toBitmap()
            val matrix = Matrix().apply {
                postRotate(image.imageInfo.rotationDegrees.toFloat())
            }
            val rotatedBitmap = Bitmap.createBitmap(
                bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true
            )
            sendFrameToServer(rotatedBitmap, serverIp)
        } catch (e: Exception) {
            Log.e("CAMERA", "Błąd przetwarzania: ${e.message}")
        } finally {
            image.close()
        }
    }

    private fun sendFrameToServer(rotatedBitmap: Bitmap, serverIp: String) {
        val stream = ByteArrayOutputStream()
        rotatedBitmap.compress(Bitmap.CompressFormat.JPEG, 30, stream)
        val byteArray = stream.toByteArray()

        val request = Request.Builder()
            .url("http://$serverIp:5000/upload_frame")
            .post(byteArray.toRequestBody("image/jpeg".toMediaType()))
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: java.io.IOException) {
                Log.e("NETWORK", "Błąd wysyłania: ${e.message}")
            }
            override fun onResponse(call: Call, response: Response) {
                response.close()
            }
        })
    }

    private fun allPermissionsGranted() = ContextCompat.checkSelfPermission(
        this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED

    override fun onDestroy() {
        super.onDestroy()
        isPollerRunning = false
        cameraExecutor.shutdown()
    }
}