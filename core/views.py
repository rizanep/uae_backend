"""Public utility views (no auth)."""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET


def _app_store_url() -> str:
    return getattr(
        settings,
        "APP_STORE_URL",
        "https://apps.apple.com/us/app/simak-fresh/id6770574538",
    )


def _play_store_url() -> str:
    return getattr(
        settings,
        "PLAY_STORE_URL",
        "https://play.google.com/store/apps/details?id=com.simakfresh.app",
    )


def _is_ios(user_agent: str) -> bool:
    ua = user_agent.lower()
    return any(token in ua for token in ("iphone", "ipad", "ipod"))


def _is_android(user_agent: str) -> bool:
    return "android" in user_agent.lower()


@require_GET
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def app_download_redirect(request):
    """Smart app download link for QR codes (iOS/Android store redirect)."""
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    if _is_ios(user_agent):
        return redirect(_app_store_url(), permanent=False)
    if _is_android(user_agent):
        return redirect(_play_store_url(), permanent=False)

    site = getattr(settings, "SITE_URL", "https://simakfresh.ae").rstrip("/")
    app_name = getattr(settings, "APP_NAME", "Simak Fresh")
    ios_url = _app_store_url()
    android_url = _play_store_url()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Download {app_name}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f4f5fa;
      color: #28316c;
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }}
    .card {{
      background: #fff;
      border-radius: 12px;
      padding: 32px 28px;
      max-width: 420px;
      width: 100%;
      text-align: center;
      box-shadow: 0 8px 24px rgba(40, 49, 108, 0.12);
    }}
    h1 {{ margin: 0 0 8px; font-size: 1.5rem; }}
    p {{ margin: 0 0 24px; color: #5a648c; line-height: 1.5; }}
    a {{
      display: block;
      margin: 10px 0;
      padding: 14px 18px;
      border-radius: 8px;
      text-decoration: none;
      font-weight: 600;
      color: #fff;
      background: #28316c;
    }}
    a.secondary {{ background: #f5b800; color: #28316c; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Download {app_name}</h1>
    <p>Get the app on your phone.</p>
    <a href="{ios_url}">Download on the App Store</a>
    <a class="secondary" href="{android_url}">Get it on Google Play</a>
    <p style="margin-top:20px;font-size:0.9rem;"><a href="{site}" style="display:inline;background:none;color:#28316c;padding:0;">{site}</a></p>
  </div>
</body>
</html>"""
    return HttpResponse(html, content_type="text/html; charset=utf-8")
