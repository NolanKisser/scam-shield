package expo.modules.smsguard

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/** Sends a message to the Scam Shield backend, stores the result, and warns the user if needed. */
object ScamChecker {
  private const val PREFS = "scam_shield"
  private const val CHANNEL_ID = "scam_alerts"
  private const val MAX_HISTORY = 50

  /** Set by SmsGuardModule while the JS app is alive, so the UI updates live. */
  @Volatile var listener: ((Map<String, Any?>) -> Unit)? = null

  private val recent = LinkedHashSet<Int>()

  fun prefs(ctx: Context): SharedPreferences = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

  /** Messaging apps re-post the same notification on updates; only check each message once. */
  fun isDuplicate(key: Int): Boolean = synchronized(recent) {
    if (!recent.add(key)) return true
    if (recent.size > 200) recent.remove(recent.first())
    false
  }

  /** Blocking network call: run off the main thread. */
  fun check(ctx: Context, sender: String, body: String): JSONObject {
    val p = prefs(ctx)
    val server = p.getString("serverUrl", "").orEmpty().trimEnd('/')
    if (server.isEmpty()) throw IllegalStateException("Set the server URL in Scam Shield first")

    val payload = JSONObject()
      .put("sender", sender)
      .put("body", body)
      .put("owner", p.getString("owner", "").orEmpty())

    val conn = URL("$server/api/device/check").openConnection() as HttpURLConnection
    val res = try {
      conn.requestMethod = "POST"
      conn.connectTimeout = 5_000
      conn.readTimeout = 30_000
      conn.doOutput = true
      conn.setRequestProperty("Content-Type", "application/json")
      conn.outputStream.use { it.write(payload.toString().toByteArray()) }
      if (conn.responseCode !in 200..299) throw IOException("Server returned ${conn.responseCode}")
      JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
    } finally {
      conn.disconnect()
    }

    val verdict = res.getJSONObject("verdict")
    val entry = JSONObject()
      .put("sender", sender)
      .put("body", body)
      .put("level", verdict.getString("risk_level"))
      .put("score", verdict.getDouble("risk_score"))
      .put("scamType", verdict.optString("scam_type"))
      .put("summary", verdict.optString("summary"))
      .put("text", res.getString("notification_text"))
      .put("guardianAlerted", res.optBoolean("guardian_alerted"))
      .put("at", System.currentTimeMillis())

    saveHistory(p, entry)
    if (res.optBoolean("notify")) showWarning(ctx, sender, res.getString("notification_text"))
    listener?.invoke(mapOf("entry" to entry.toString()))
    return entry
  }

  @Synchronized
  private fun saveHistory(p: SharedPreferences, entry: JSONObject) {
    val old = JSONArray(p.getString("history", "[]"))
    val next = JSONArray().put(entry)
    for (i in 0 until minOf(old.length(), MAX_HISTORY - 1)) next.put(old.get(i))
    p.edit().putString("history", next.toString()).apply()
  }

  private fun showWarning(ctx: Context, sender: String, text: String) {
    val nm = NotificationManagerCompat.from(ctx)
    if (!nm.areNotificationsEnabled()) return

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
      val channel = NotificationChannel(CHANNEL_ID, "Scam warnings", NotificationManager.IMPORTANCE_HIGH)
      channel.description = "Warnings about suspicious texts"
      ctx.getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    val open = ctx.packageManager.getLaunchIntentForPackage(ctx.packageName)?.let {
      PendingIntent.getActivity(ctx, 0, it, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    }

    val notification = NotificationCompat.Builder(ctx, CHANNEL_ID)
      .setSmallIcon(android.R.drawable.ic_dialog_alert)
      .setContentTitle("Possible scam from $sender")
      .setContentText(text.lineSequence().firstOrNull().orEmpty())
      .setStyle(NotificationCompat.BigTextStyle().bigText(text))
      .setPriority(NotificationCompat.PRIORITY_HIGH)
      .setCategory(NotificationCompat.CATEGORY_MESSAGE)
      .setAutoCancel(true)
      .setContentIntent(open)
      .build()

    try {
      nm.notify((sender + text).hashCode(), notification)
    } catch (_: SecurityException) {
      // POST_NOTIFICATIONS was revoked; the verdict is still in the in-app history.
    }
  }
}
