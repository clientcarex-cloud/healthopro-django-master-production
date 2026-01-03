import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healtho_pro.settings')
django.setup()

from healtho_pro_user.models.users_models import Client, Domain

try:
    # 1. Get the 'demo' tenant
    target_tenant_name = 'demo' # Using 'demo' schema as target
    try:
        new_tenant = Client.objects.get(schema_name=target_tenant_name)
    except Client.DoesNotExist:
        print(f"Tenant '{target_tenant_name}' not found. Falling back to creating one or trying another.")
        # Fallback: check if 'HealthoproDemo' exists
        target_tenant_name = 'HealthoproDemo'
        new_tenant = Client.objects.get(schema_name='HealthoproDemo')
    
    print(f"Targeting tenant: {new_tenant.name} ({new_tenant.schema_name})")

    # 2. Find localhost domain
    domains = Domain.objects.filter(domain__in=['localhost', '127.0.0.1'])
    
    if not domains.exists():
        print("Localhost domains not found. Creating them...")
        Domain.objects.create(domain='localhost', tenant=new_tenant, is_primary=False)
        Domain.objects.create(domain='127.0.0.1', tenant=new_tenant, is_primary=False)
    else:
        for d in domains:
            print(f"Updating {d.domain} from {d.tenant.schema_name} to {new_tenant.schema_name}")
            d.tenant = new_tenant
            d.save()
            
    print("Successfully mapped localhost/127.0.0.1 to tenant:", new_tenant.schema_name)

except Exception as e:
    print(f"Error: {e}")
