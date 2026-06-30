from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'job', 'status', 'applied_at']
    list_filter = ['status']
    search_fields = ['candidate__username', 'job__title']
    # Admin saves also go through the model's save() -> post_save signals
    # fire exactly the same way they would from the regular views above.
