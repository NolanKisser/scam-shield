package expo.modules.smsguard

import android.content.Intent
import android.provider.Settings
import androidx.core.app.NotificationManagerCompat
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class SmsGuardModule : Module() {
  private val context
    get() = requireNotNull(appContext.reactContext)

  override fun definition() = ModuleDefinition {
    Name("SmsGuard")

    Events("onVerdict")

    OnCreate {
      ScamChecker.listener = { payload -> this@SmsGuardModule.sendEvent("onVerdict", payload) }
    }

    OnDestroy {
      ScamChecker.listener = null
    }

    Function("isAccessGranted") {
      NotificationManagerCompat.getEnabledListenerPackages(context).contains(context.packageName)
    }

    Function("openAccessSettings") {
      context.startActivity(
        Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
      )
    }

    Function("getConfig") {
      val p = ScamChecker.prefs(context)
      mapOf(
        "serverUrl" to p.getString("serverUrl", "").orEmpty(),
        "owner" to p.getString("owner", "").orEmpty(),
        "enabled" to p.getBoolean("enabled", true),
      )
    }

    Function("setConfig") { serverUrl: String, owner: String, enabled: Boolean ->
      ScamChecker.prefs(context).edit()
        .putString("serverUrl", serverUrl.trim())
        .putString("owner", owner.trim())
        .remove("checkContacts") // setting removed; clear it from older installs
        .putBoolean("enabled", enabled)
        .apply()
    }

    Function("getHistory") {
      ScamChecker.prefs(context).getString("history", "[]")
    }

    Function("clearHistory") {
      ScamChecker.prefs(context).edit().remove("history").apply()
    }

    // Runs the same check the background service runs; handy for demos and testing.
    AsyncFunction("testCheck") { sender: String, body: String ->
      ScamChecker.check(context, sender, body).toString()
    }
  }
}
