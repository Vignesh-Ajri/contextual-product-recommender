import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100)
    event_type = models.CharField(max_length=50) # e.g. 'view', 'cart', 'purchase', 'search'
    
    # Optional references
    product_id = models.UUIDField(null=True, blank=True)
    category_id = models.IntegerField(null=True, blank=True)
    
    # CPRP specific context (extracted from product/category if available)
    cprp_category = models.CharField(max_length=100, null=True, blank=True)
    cprp_brand = models.CharField(max_length=100, null=True, blank=True)
    cprp_price_range = models.CharField(max_length=50, null=True, blank=True)
    cprp_product_name = models.CharField(max_length=255, null=True, blank=True)
    
    search_query = models.CharField(max_length=255, null=True, blank=True)
    
    page_url = models.CharField(max_length=500, null=True, blank=True)
    referrer = models.CharField(max_length=500, null=True, blank=True)
    
    device_type = models.CharField(max_length=50, null=True, blank=True)
    platform = models.CharField(max_length=50, null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    synced_to_cprp = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.event_type} - {self.session_id}"
