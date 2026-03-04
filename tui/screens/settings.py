"""Settings screen - API keys, provider, language."""
from prompt_toolkit import prompt as pt_prompt
from tui.components import (console, print_header, print_success, print_error,
                            print_warning, print_info, with_spinner, build_summary_table)
from tui.menus import get_keypress
from ai.provider_registry import PROVIDER_META, list_providers
from core.keychain import save_key, get_all_keys, delete_key, count_keys
from core import config


def run_settings(session: dict) -> None:
    """Settings screen."""
    while True:
        print_header("SETTINGS")

        api_manager = session.get("api_manager")
        provider_name = config.get_active_provider()
        meta = PROVIDER_META.get(provider_name, {})

        # Current provider panel
        summary = {
            "Active Provider": meta.get("label", provider_name),
            "Model": config.get_active_model(),
            "Keys Stored": count_keys(provider_name),
            "Language": config.get_language(),
        }
        console.print(build_summary_table(summary, "Current Configuration"))
        console.print()

        # Menu
        console.print("  [key][1][/] Switch provider")
        console.print("  [key][2][/] Add API key")
        console.print("  [key][3][/] Remove API key")
        console.print("  [key][4][/] Test connection")
        console.print("  [key][5][/] Change model")
        console.print("  [key][6][/] Change language")
        console.print("  [key][B][/] Back")
        console.print()

        key = get_keypress()

        if key == "b":
            return
        elif key == "1":
            _switch_provider(session)
        elif key == "2":
            _add_key(session)
        elif key == "3":
            _remove_key(session)
        elif key == "4":
            _test_connection(session)
        elif key == "5":
            _change_model()
        elif key == "6":
            _change_language()


def _switch_provider(session: dict):
    """Switch AI provider."""
    providers = list_providers()
    console.print("\n  Available providers:")
    for i, name in enumerate(providers, 1):
        meta = PROVIDER_META[name]
        label = meta["label"]
        free = " (free)" if meta["free_tier"] else ""
        local = " (local)" if meta["local"] else ""
        console.print(f"    [{i}] {label}{free}{local}")

    try:
        choice = pt_prompt("\n  Select provider number: ")
        idx = int(choice) - 1
        if 0 <= idx < len(providers):
            new_provider = providers[idx]
            config.set_active_provider(new_provider)
            _reinit_api_manager(session)
            print_success(f"Switched to {PROVIDER_META[new_provider]['label']}")
        else:
            print_error("Invalid selection.")
    except (ValueError, KeyboardInterrupt, EOFError):
        pass


def _add_key(session: dict):
    """Add API key with hidden input and validation."""
    provider = config.get_active_provider()
    meta = PROVIDER_META.get(provider, {})

    if meta.get("local", False):
        print_info("Local provider (Ollama) doesn't require an API key.")
        return

    console.print(f"\n  Adding key for [key]{meta.get('label', provider)}[/]")
    if meta.get("key_prefix"):
        console.print(f"  [info]Key should start with: {meta['key_prefix']}[/]")

    try:
        key = pt_prompt("  API Key: ", is_password=True)
    except (KeyboardInterrupt, EOFError):
        return

    if not key.strip():
        print_warning("No key entered.")
        return

    # Save key
    idx = count_keys(provider)
    if save_key(provider, key.strip(), idx):
        print_success(f"Key saved to OS Keychain (slot {idx})")
        _reinit_api_manager(session)

        # Validate
        if session.get("api_manager"):
            valid = with_spinner("Validating key...", session["api_manager"].validate_current_key)
            if valid:
                print_success("Key validated successfully!")
            else:
                print_warning("Key saved but validation failed. It may still work.")
    else:
        print_error("Failed to save key to keychain.")


def _remove_key(session: dict):
    """Remove an API key."""
    provider = config.get_active_provider()
    keys = get_all_keys(provider)

    if not keys:
        print_warning("No keys stored for this provider.")
        return

    console.print(f"\n  Keys for {provider}:")
    for i, k in enumerate(keys):
        masked = k[:4] + "..." + k[-4:] if len(k) > 8 else "****"
        console.print(f"    [{i}] {masked}")

    try:
        choice = pt_prompt("\n  Key index to remove: ")
        idx = int(choice)
        if 0 <= idx < len(keys):
            if delete_key(provider, idx):
                print_success(f"Key {idx} removed")
                _reinit_api_manager(session)
            else:
                print_error("Failed to remove key")
        else:
            print_error("Invalid index")
    except (ValueError, KeyboardInterrupt, EOFError):
        pass


def _test_connection(session: dict):
    """Test current API connection."""
    api_manager = session.get("api_manager")
    if not api_manager:
        print_warning("No API manager configured. Add a key first.")
        return

    valid = with_spinner("Testing connection...", api_manager.validate_current_key)
    if valid:
        print_success("Connection successful!")
    else:
        print_error("Connection failed. Check your API key and network.")


def _change_model():
    """Change active model."""
    provider = config.get_active_provider()
    meta = PROVIDER_META.get(provider, {})
    models = meta.get("models", [])

    if not models:
        try:
            model = pt_prompt(f"  Enter model name for {provider}: ")
            if model.strip():
                config.set_active_model(model.strip())
                print_success(f"Model set to: {model.strip()}")
        except (KeyboardInterrupt, EOFError):
            pass
        return

    console.print(f"\n  Available models for {meta.get('label', provider)}:")
    for i, m in enumerate(models, 1):
        current = " (current)" if m == config.get_active_model() else ""
        console.print(f"    [{i}] {m}{current}")

    try:
        choice = pt_prompt("\n  Select model number: ")
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            config.set_active_model(models[idx])
            print_success(f"Model set to: {models[idx]}")
        else:
            print_error("Invalid selection.")
    except (ValueError, KeyboardInterrupt, EOFError):
        pass


def _change_language():
    """Change interpretation language."""
    console.print("\n  Common languages: English, Indonesian, Spanish, French, German, Japanese, Chinese")
    try:
        lang = pt_prompt("  Language: ")
        if lang.strip():
            config.set_language(lang.strip())
            print_success(f"Language set to: {lang.strip()}")
    except (KeyboardInterrupt, EOFError):
        pass


def _reinit_api_manager(session: dict):
    """Re-initialize API manager after changes."""
    from ai.api_manager import init_from_config
    session["api_manager"] = init_from_config()
