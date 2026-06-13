import os
import sys
from pathlib import Path

# Resolve base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR / "scripts" / "news_engine"))

try:
    from impact_engine import ImpactEngine
except ImportError as e:
    print(f"Failed to import ImpactEngine: {e}")
    sys.exit(1)

# Reconfigure stdout to use UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def run_scenarios():
    print("=========================================================")
    print("    MARKET_INTEL v4.0 - IMPACT PROPAGATION TEST SUITE    ")
    print("=========================================================")
    
    engine = ImpactEngine()
    
    scenarios = [
        # Scenario 1: Anthropic AI Shutdown
        {
            "title": "Anthropic Claude API Experiences Full Service Shutdown due to Server Farm Outage",
            "source": "Bloomberg",
            "event_type": "Technology",
            "expectation_changed": "Supply Shock",
            "first_order_node": "Anthropic Claude",
            "initial_direction": "BEARISH",
            "raw_magnitude": 90.0,
            "initial_conviction": 95.0,
            "signal_date": "2026-06-12",
            "signal_horizon": "Swing",
            "related_theme": "Technology"
        },
        # Scenario 2: Oil Supply Shock
        {
            "title": "Middle East Tensions Escalate; Brent Crude Oil Spikes 5% Past $95/bbl",
            "source": "Reuters",
            "event_type": "Commodity",
            "expectation_changed": "Pricing",
            "first_order_node": "Brent Crude",
            "initial_direction": "BULLISH",
            "raw_magnitude": 85.0,
            "initial_conviction": 90.0,
            "signal_date": "2026-06-12",
            "signal_horizon": "3 Month",
            "related_theme": "Energy"
        },
        # Scenario 3: Defense Capital Allocations
        {
            "title": "Ministry of Defense Announces 15% Increase in Annual Capital Allocation for Domestic Procurement",
            "source": "BSE Notice",
            "event_type": "Regulatory",
            "expectation_changed": "Demand",
            "first_order_node": "Indian Defense Allocation",
            "initial_direction": "BULLISH",
            "raw_magnitude": 95.0,
            "initial_conviction": 100.0,
            "signal_date": "2026-06-12",
            "signal_horizon": "1 Year",
            "related_theme": "Defense"
        },
        # Scenario 4: Taiwan Strait Shipping Blockade (Semiconductors)
        {
            "title": "Taiwan Strait Shipping Blockade Disrupts Silicon Foundry Contract Shipments",
            "source": "Reuters",
            "event_type": "Geopolitical",
            "expectation_changed": "Supply Shock",
            "first_order_node": "Taiwan Foundry Disruption",
            "initial_direction": "BULLISH",
            "raw_magnitude": 80.0,
            "initial_conviction": 90.0,
            "signal_date": "2026-06-12",
            "signal_horizon": "3 Month",
            "related_theme": "Semiconductors"
        },
        # Scenario 5: Solid-State Battery Commercialization
        {
            "title": "Major OEM Announces Breakthrough Commercialization Timeline for Solid-State Batteries",
            "source": "Reuters",
            "event_type": "Technology",
            "expectation_changed": "Demand",
            "first_order_node": "Solid-State Battery",
            "initial_direction": "BULLISH",
            "raw_magnitude": 85.0,
            "initial_conviction": 90.0,
            "signal_date": "2026-06-12",
            "signal_horizon": "Multi-Year",
            "related_theme": "Electric Vehicles"
        }
    ]
    
    total_signals_generated = 0
    
    for idx, sc in enumerate(scenarios, 1):
        print(f"\n--- Running Scenario {idx} of {len(scenarios)} ---")
        signals = engine.process_impact_event(
            article_title=sc["title"],
            source=sc["source"],
            event_type=sc["event_type"],
            expectation_changed=sc["expectation_changed"],
            first_order_node=sc["first_order_node"],
            initial_direction=sc["initial_direction"],
            raw_magnitude=sc["raw_magnitude"],
            initial_conviction=sc["initial_conviction"],
            signal_date=sc["signal_date"],
            signal_horizon=sc["signal_horizon"],
            related_theme=sc["related_theme"]
        )
        total_signals_generated += len(signals)
        print(f"Scenario {idx} complete. Mapped {len(signals)} listed companies.")
        
    print("\n=========================================================")
    print(f"Impact Propagation test run complete. Generated {total_signals_generated} signals.")
    print("=========================================================")

if __name__ == "__main__":
    run_scenarios()
