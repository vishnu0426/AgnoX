#!/usr/bin/env python3
"""
LiveKit SIP Trunk Diagnostic Script
Checks if your trunks are properly configured
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from livekit import api
from config.settings import settings


async def diagnose_trunks():
    """Diagnose LiveKit SIP trunk configuration"""
    
    print("=" * 70)
    print("LiveKit SIP Trunk Diagnostic")
    print("=" * 70)
    print()
    
    # Check settings
    print("📋 Configuration Check:")
    print(f"   LiveKit URL: {settings.livekit_url}")
    print(f"   Inbound Trunk ID: {settings.default_inbound_trunk_id}")
    print(f"   Outbound Trunk ID: {settings.default_outbound_trunk_id}")
    print(f"   Caller ID: {settings.default_caller_id}")
    print()
    
    # Create API client
    try:
        lk_api = api.LiveKitAPI(
            url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret
        )
        print("✅ LiveKit API client created successfully")
        print()
    except Exception as e:
        print(f"❌ Failed to create LiveKit API client: {e}")
        return
    
    # List all inbound trunks
    print("📥 Inbound Trunks:")
    print("-" * 70)
    try:
        inbound_response = await lk_api.sip.list_sip_inbound_trunk(
            api.ListSIPInboundTrunkRequest()
        )
        
        if not inbound_response.items:
            print("⚠️  No inbound trunks found!")
            print()
        else:
            for trunk in inbound_response.items:
                trunk_id = trunk.sip_trunk_id
                name = trunk.name
                numbers = list(trunk.numbers) if trunk.numbers else []
                
                status = "✅" if trunk_id == settings.default_inbound_trunk_id else "  "
                print(f"{status} Trunk ID: {trunk_id}")
                print(f"   Name: {name}")
                print(f"   Numbers: {numbers}")
                print()
    except Exception as e:
        print(f"❌ Error listing inbound trunks: {e}")
        print()
    
    # List all outbound trunks
    print("📤 Outbound Trunks:")
    print("-" * 70)
    try:
        outbound_response = await lk_api.sip.list_sip_outbound_trunk(
            api.ListSIPOutboundTrunkRequest()
        )
        
        if not outbound_response.items:
            print("⚠️  No outbound trunks found!")
            print()
            print("🔧 You need to create an outbound trunk in LiveKit Cloud:")
            print("   1. Go to: https://cloud.livekit.io/")
            print("   2. Navigate to: Project Settings > SIP")
            print("   3. Create an outbound trunk")
            print("   4. Copy the trunk ID to your .env file")
            print()
        else:
            for trunk in outbound_response.items:
                trunk_id = trunk.sip_trunk_id
                name = trunk.name
                address = getattr(trunk, 'address', 'N/A')
                numbers = list(trunk.numbers) if trunk.numbers else []
                
                status = "✅" if trunk_id == settings.default_outbound_trunk_id else "  "
                print(f"{status} Trunk ID: {trunk_id}")
                print(f"   Name: {name}")
                print(f"   Address: {address}")
                print(f"   Numbers: {numbers}")
                print()
    except Exception as e:
        print(f"❌ Error listing outbound trunks: {e}")
        print()
    
    # List dispatch rules
    print("📋 Dispatch Rules:")
    print("-" * 70)
    try:
        dispatch_response = await lk_api.sip.list_sip_dispatch_rule(
            api.ListSIPDispatchRuleRequest()
        )
        
        if not dispatch_response.items:
            print("⚠️  No dispatch rules found!")
            print()
            print("🔧 You need to create a dispatch rule for inbound calls:")
            print("   Run: python scripts/create_dispatch_rule.py")
            print()
        else:
            for rule in dispatch_response.items:
                rule_id = rule.sip_dispatch_rule_id
                name = rule.name
                trunk_ids = list(rule.trunk_ids) if rule.trunk_ids else []
                
                print(f"   Rule ID: {rule_id}")
                print(f"   Name: {name}")
                print(f"   Trunk IDs: {trunk_ids}")
                print()
    except Exception as e:
        print(f"❌ Error listing dispatch rules: {e}")
        print()
    
    # Summary
    print("=" * 70)
    print("Summary & Recommendations:")
    print("=" * 70)
    print()
    
    # Check if configured trunk exists
    if settings.default_outbound_trunk_id:
        print("🔍 Checking if your configured outbound trunk exists...")
        found = False
        try:
            outbound_response = await lk_api.sip.list_sip_outbound_trunk(
                api.ListSIPOutboundTrunkRequest()
            )
            for trunk in outbound_response.items:
                if trunk.sip_trunk_id == settings.default_outbound_trunk_id:
                    found = True
                    print(f"✅ Outbound trunk {settings.default_outbound_trunk_id} EXISTS")
                    break
            
            if not found:
                print(f"❌ Outbound trunk {settings.default_outbound_trunk_id} NOT FOUND")
                print()
                print("🔧 Fix:")
                print("   1. Check LiveKit dashboard for correct trunk ID")
                print("   2. Update DEFAULT_OUTBOUND_TRUNK_ID in .env")
                print("   3. OR create a new outbound trunk in LiveKit")
        except Exception as e:
            print(f"❌ Error checking trunk: {e}")
    else:
        print("⚠️  DEFAULT_OUTBOUND_TRUNK_ID is not set in .env")
    
    print()


if __name__ == '__main__':
    try:
        asyncio.run(diagnose_trunks())
    except KeyboardInterrupt:
        print("\n\nDiagnostic cancelled")
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()