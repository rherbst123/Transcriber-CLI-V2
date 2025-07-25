
from cost_analysis import CostTracker

def main():
    print("=" * 80)
    print("AWS BEDROCK MODEL PRICING INFORMATION")
    print("=" * 80)
    print("All prices are per 1 million tokens (USD)")
    print()
    
    tracker = CostTracker()
    
    for model_id, pricing in tracker.MODEL_PRICING.items():
        # Extract readable model name
        model_name = model_id.split(".")[-1].replace("-v1:0", "")
        provider = model_id.split(".")[1]
        
        print(f"Model: {model_name}")
        print(f"Provider: {provider.title()}")
        print(f"Input Tokens:  ${pricing['input']*1000:.2f} per 1M tokens")
        print(f"Output Tokens: ${pricing['output']*1000:.2f} per 1M tokens")
        print("-" * 50)
    
    print("\nNotes:")
    print("• Prices are estimates based on AWS Bedrock pricing as of 2025")
    print("• Actual costs may vary based on AWS pricing updates")
    print("• Token counts in reports are estimated (4 characters ≈ 1 token)")
    print("• Image processing may include additional base costs")
    print("=" * 80)

if __name__ == "__main__":
    main()