"""
Turkey E-License System — CLI application.
"""
import sys
from pathlib import Path

from cities import list_city_summaries
from services.issuer import LicenseIssuer
import config


def print_menu(city_name: str):
    print("\n" + "=" * 60)
    print(f"  {city_name.upper()} — TURKEY E-LICENSE CLI")
    print("=" * 60)
    print("\n1. Issue new license")
    print("2. Verify license")
    print("3. Get license info")
    print("4. Change municipality")
    print("5. Exit")
    print("\n" + "=" * 60)


def choose_city() -> str:
    cities = list_city_summaries()
    print("\nSelect municipality:")
    for index, city in enumerate(cities, start=1):
        print(f"  {index}. {city['name']} ({city['license_prefix']})")
    default_index = next(
        (i for i, c in enumerate(cities) if c["slug"] == config.CITY_SLUG),
        0,
    )
    choice = input(f"\nChoice [default {default_index + 1}]: ").strip()
    if not choice:
        return cities[default_index]["slug"]
    try:
        return cities[int(choice) - 1]["slug"]
    except (ValueError, IndexError):
        print("   Invalid choice, using default.")
        return config.CITY_SLUG


def issue_license_interactive(issuer: LicenseIssuer, city_slug: str):
    from cities import get_city

    city = get_city(city_slug)
    print(f"\n  ISSUE NEW LICENSE — {city['name']}")
    print("-" * 60)

    example = city["license_id_example"]
    license_data = {
        "license_id": input(f"License ID (e.g. {example}): ").strip(),
        "license_type": input("License Type (e.g. Restaurant): ").strip(),
        "owner_name": input("Owner Name: ").strip(),
        "business_name": input("Business Name: ").strip(),
        "address": input("Address: ").strip(),
        "citizen_id": input("National ID: ").strip(),
        "region": input(f"District ({', '.join(city['districts'][:3])}...): ").strip(),
        "issue_date": input("Issue Date (YYYY-MM-DD): ").strip(),
        "expiry_date": input("Expiry Date (YYYY-MM-DD): ").strip(),
    }

    pdf_path = input("PDF Path (press Enter to skip): ").strip()
    if pdf_path and not Path(pdf_path).exists():
        print(f"   PDF file not found: {pdf_path}")
        pdf_path = None

    try:
        result = issuer.issue_license(
            license_data,
            pdf_path or None,
            city_slug=city_slug,
        )
        if result["success"]:
            print(f"\n   License issued for {result['city_name']}!")
            print(f"  QR: {result['qr_url']}")
            if result.get("ipfs_hash"):
                print(f"  IPFS: {result['ipfs_hash']}")
    except Exception as exc:
        print(f"\n   Error: {exc}")


def verify_license_interactive(issuer: LicenseIssuer, city_slug: str):
    print(f"\n  VERIFY LICENSE")
    print("-" * 60)
    license_id = input("Enter License ID: ").strip()
    info = issuer.get_license_info(license_id, city_slug=city_slug)

    if not info:
        print(f"\n   License not found: {license_id}")
        return

    print(f"\n   LICENSE FOUND ({info.get('city_name', city_slug)})")
    for key in (
        "license_id", "license_type", "owner_name", "business_name",
        "region", "issue_date", "expiry_date", "authority",
    ):
        print(f"   {key}: {info.get(key)}")


def main():
    print("\n  Starting Turkey E-License Platform (CLI)...")
    city_slug = choose_city()

    try:
        issuer = LicenseIssuer()
    except Exception as exc:
        print(f"   Failed to initialize: {exc}")
        return

    while True:
        from cities import get_city
        print_menu(get_city(city_slug)["name"])
        choice = input("\nSelect option (1-5): ").strip()

        if choice == "1":
            issue_license_interactive(issuer, city_slug)
        elif choice == "2":
            verify_license_interactive(issuer, city_slug)
        elif choice == "3":
            license_id = input("Enter License ID: ").strip()
            info = issuer.get_license_info(license_id, city_slug=city_slug)
            if info:
                import json
                print(json.dumps(info, indent=2, ensure_ascii=False))
            else:
                print("   License not found")
        elif choice == "4":
            city_slug = choose_city()
        elif choice == "5":
            print("\n  Goodbye!")
            break
        else:
            print("   Invalid option")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
