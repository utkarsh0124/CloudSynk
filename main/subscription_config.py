SUBSCRIPTION_CHOICES = (
    ("TESTER", "Tester"),
    ("STARTER", "Starter"),
    ("STANDARD", "Standard"),
    ("PREMIUM", "Premium"),
    ("PREMIUM_PLUS", "PremiumPlus"),
    ("OWNER", "Owner"),
)

SUBSCRIPTION_VALUES = {
    "TESTER": 1048576,   # 1 MB
    "STARTER": 1073741824,   # 1 GB
    "STANDARD": 2147483648,  # 2 GB
    "PREMIUM": 10737418240,  # 10 GB
    "PREMIUM_PLUS": 107374182400,  # 100 GB
    "OWNER": 1099511627776  # 1 TB
}