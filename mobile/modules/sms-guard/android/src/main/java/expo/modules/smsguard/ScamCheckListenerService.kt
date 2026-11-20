package expo.modules.smsguard

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import java.util.concurrent.Executors

/**
 * Sees every notification once the user grants Notification access. We only act on
 * notifications from texting apps, and only when the sender isn't a saved contact
 * (the title is a raw phone number instead of a name). Everything else is ignored on the spot.
 */
class ScamCheckListenerService : NotificationListenerService() {
  private val executor = Executors.newSingleThreadExecutor()

  override fun onNotificationPosted(sbn: StatusBarNotification) {
    if (sbn.packageName !in SMS_APPS) return
    val n = sbn.notification
    if (n.flags and Notification.FLAG_GROUP_SUMMARY != 0) return

    if (!ScamChecker.prefs(this).getBoolean("enabled", true)) return

    // Saved contacts show up as a name, unknown senders as a raw number. Decide from the
    // sender alone, so a contact's message text is never read, stored, or sent anywhere.
    val extras = n.extras
    val sender = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()?.trim().orEmpty()
    if (!looksUnknown(sender)) return

    val body = (extras.getCharSequence(Notification.EXTRA_BIG_TEXT)
      ?: extras.getCharSequence(Notification.EXTRA_TEXT))?.toString()?.trim().orEmpty()
    if (body.isEmpty()) return
    if (ScamChecker.isDuplicate((sender + "\u0000" + body).hashCode())) return

    executor.execute {
      try {
        ScamChecker.check(applicationContext, sender, body)
      } catch (e: Exception) {
        Log.w(TAG, "Scam check failed", e)
      }
    }
  }

  override fun onDestroy() {
    executor.shutdown()
    super.onDestroy()
  }

  companion object {
    private const val TAG = "ScamShield"

    val SMS_APPS = setOf(
      "com.google.android.apps.messaging", // Google Messages
      "com.samsung.android.messaging",     // Samsung Messages
      "com.android.mms",
      "com.android.messaging",
      "com.motorola.messaging",
      "com.oneplus.mms",
    )

    // "+1 202-555-0143", "(202) 555-0143", short codes like "72975", or email senders
    private val PHONE_LIKE = Regex("^[+(\\d][\\d\\s().-]{3,}$")

    fun looksUnknown(sender: String) = PHONE_LIKE.matches(sender) || '@' in sender
  }
}
