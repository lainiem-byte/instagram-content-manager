import json
import os
import sys

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'brand-profiles.json')

def load_profiles():
    if not os.path.exists(CONFIG_PATH):
        return []
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_profiles(profiles):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, indent=2)

def show_profiles(profiles):
    print("\n--- Brand Profiles ---")
    if not profiles:
        print("No profiles found.")
        return
    for i, p in enumerate(profiles):
        status = "[ACTIVE]" if p.get('active') else "[INACTIVE]"
        print(f"{i + 1}. {p.get('account_id')} ({p.get('brand_name')}) {status}")
    print("----------------------")

def add_profile(profiles):
    print("\n--- Add New Profile ---")
    account_id = input("Account ID (e.g., lnlaiagency_main): ").strip()
    brand_name = input("Brand Name: ").strip()
    instagram_handle = input("Instagram Handle: ").strip()
    brand_voice = input("Brand Voice (e.g., bold, authoritative): ").strip()
    aesthetic = input("Aesthetic: ").strip()
    tone_keywords_raw = input("Tone Keywords (comma separated): ").strip()
    branded_hashtags_raw = input("Branded Hashtags (comma separated): ").strip()
    call_to_action = input("Call to Action: ").strip()
    drive_folder_id = input("Drive Folder ID: ").strip()
    drive_account = input("Drive Account Email: ").strip()
    post_link = input("Post Link: ").strip()
    sheets_log_name = input("Sheets Log Name [Instagram Post Log]: ").strip() or "Instagram Post Log"
    active_raw = input("Active? (y/n) [y]: ").strip().lower()
    
    new_profile = {
        "account_id": account_id,
        "brand_name": brand_name,
        "instagram_handle": instagram_handle,
        "brand_voice": brand_voice,
        "aesthetic": aesthetic,
        "tone_keywords": [k.strip() for k in tone_keywords_raw.split(',')] if tone_keywords_raw else [],
        "branded_hashtags": [h.strip() for h in branded_hashtags_raw.split(',')] if branded_hashtags_raw else [],
        "call_to_action": call_to_action,
        "drive_folder_id": drive_folder_id,
        "drive_account": drive_account,
        "post_link": post_link,
        "sheets_log_name": sheets_log_name,
        "active": active_raw != 'n'
    }
    profiles.append(new_profile)
    save_profiles(profiles)
    print(f"Profile '{account_id}' added successfully!")

def toggle_active(profiles):
    show_profiles(profiles)
    if not profiles: return
    try:
        idx = int(input("\nEnter profile number to toggle active status: ").strip()) - 1
        if 0 <= idx < len(profiles):
            profiles[idx]['active'] = not profiles[idx].get('active', False)
            save_profiles(profiles)
            print(f"Toggled profile {profiles[idx]['account_id']} active status to {profiles[idx]['active']}")
        else:
            print("Invalid profile number.")
    except ValueError:
        print("Please enter a valid number.")

def main():
    while True:
        profiles = load_profiles()
        print("\n=== Profile Manager ===")
        print("1. View Profiles")
        print("2. Add Profile")
        print("3. Toggle Active Status")
        print("4. Exit")
        choice = input("Select an option: ").strip()
        
        if choice == '1':
            show_profiles(profiles)
        elif choice == '2':
            add_profile(profiles)
        elif choice == '3':
            toggle_active(profiles)
        elif choice == '4':
            print("Exiting...")
            sys.exit(0)
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
