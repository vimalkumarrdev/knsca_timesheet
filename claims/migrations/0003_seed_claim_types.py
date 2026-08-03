from django.db import migrations

CLAIM_TYPES = [
    "Lunch expense",
    "Late evening snacks",
    "Dinner expense",
    "Metro charges",
    "Cab Charges",
    "Auto Charges",
    "Petrol Conveyance",
    "Misc Expenses",
]


def seed_claim_types(apps, schema_editor):
    ClaimType = apps.get_model("claims", "ClaimType")
    for name in CLAIM_TYPES:
        ClaimType.objects.get_or_create(name=name)


def remove_claim_types(apps, schema_editor):
    ClaimType = apps.get_model("claims", "ClaimType")
    ClaimType.objects.filter(name__in=CLAIM_TYPES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("claims", "0002_claimtype_alter_claim_claim_type"),
    ]

    operations = [
        migrations.RunPython(seed_claim_types, remove_claim_types),
    ]
