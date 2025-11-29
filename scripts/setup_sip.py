import asyncio
import os
import sys
from pathlib import Path
from livekit import api
from dotenv import load_dotenv

# Make project root importable and load env vars
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()


async def setup_sip_trunk():
    """Setup SIP trunk and dispatch rules"""

    livekit_url = os.getenv("LIVEKIT_URL")
    livekit_key = os.getenv("LIVEKIT_API_KEY")
    livekit_secret = os.getenv("LIVEKIT_API_SECRET")

    if not all([livekit_url, livekit_key, livekit_secret]):
        print("ERROR: Missing LiveKit credentials in environment")
        return False

    try:
        # Use async context so the aiohttp session is closed cleanly
        async with api.LiveKitAPI(
            url=livekit_url,
            api_key=livekit_key,
            api_secret=livekit_secret,
        ) as lkapi:

            print("Connected to LiveKit")

            # Try to reuse an existing trunk if SIP_TRUNK_ID is set
            existing_trunk_id = os.getenv("SIP_TRUNK_ID")

            if existing_trunk_id:
                print(
                    f"Found existing SIP_TRUNK_ID in environment, "
                    f"reusing trunk: {existing_trunk_id}"
                )
                trunk_id = existing_trunk_id

                # Only used for display
                trunk_phone = input(
                    "Enter the phone number associated with this trunk "
                    "(e.g., +1234567890): "
                ).strip()

                if not trunk_phone:
                    print(
                        "WARNING: No phone number entered; "
                        "continuing with trunk reuse."
                    )
                    trunk_phone = "<unknown>"

            else:
                print("No existing SIP_TRUNK_ID found, creating inbound SIP trunk...")

                trunk_phone = input(
                    "Enter your phone number (e.g., +1234567890): "
                ).strip()
                if not trunk_phone:
                    print("ERROR: Phone number is required")
                    return False

                # You may see a deprecation warning for create_sip_inbound_trunk,
                # but it still works. You can switch to create_inbound_trunk if you prefer.
                trunk = await lkapi.sip.create_sip_inbound_trunk(
                    api.CreateSIPInboundTrunkRequest(
                        trunk=api.SIPInboundTrunkInfo(
                            name="customer-service-inbound",
                            numbers=[trunk_phone],
                        )
                    )
                )

                trunk_id = trunk.sip_trunk_id
                print(f"Created SIP trunk: {trunk_id}")

                # Persist SIP_TRUNK_ID so future runs reuse it
                env_path = Path(__file__).parent.parent / ".env"
                # Only append if the file exists, mirroring your original behavior
                if env_path.exists():
                    with open(env_path, "a", encoding="utf-8") as f:
                        f.write(f"\nSIP_TRUNK_ID={trunk_id}\n")
                    print("Saved SIP_TRUNK_ID to .env")

            print("Creating dispatch rule...")

            # IMPORTANT FIX:
            # The field on SIPDispatchRule is `dispatch_rule_direct`,
            # not `direct`.
            dispatch = await lkapi.sip.create_sip_dispatch_rule(
                api.CreateSIPDispatchRuleRequest(
                    rule=api.SIPDispatchRule(
                        dispatch_rule_direct=api.SIPDispatchRuleDirect(
                            room_name="call-{call_id}",
                            pin="",
                        )
                    ),
                    trunk_ids=[trunk_id],
                    name="main-customer-service-queue",
                    hide_phone_number=False,
                    metadata=(
                        '{"service": "customer_service", '
                        '"phone_number": "{caller_number}"}'
                    ),
                )
            )

            print(f"Created dispatch rule: {dispatch.sip_dispatch_rule_id}")
            print("\nSIP setup completed successfully!")
            print(f"Your service number: {trunk_phone}")
            print(f"Using SIP trunk: {trunk_id}")

            return True

    except Exception as e:
        print(f"Error setting up SIP: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(setup_sip_trunk())
    sys.exit(0 if success else 1)
