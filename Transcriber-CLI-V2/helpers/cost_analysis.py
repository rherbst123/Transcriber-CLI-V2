import time
import os
from datetime import datetime
from pathlib import Path

def get_output_base_path():
    """Get the base output path, cross-platform compatible"""
    home_dir = Path(os.path.expanduser("~"))
    
    # On Windows, prefer Desktop if it exists
    if os.name == 'nt':  # Windows
        desktop_path = home_dir / "Desktop"
        if desktop_path.exists():
            return desktop_path / "Finished Transcriptions"
    
    # On Unix systems or if Desktop doesn't exist, use a directory in home
    return home_dir / "Finished Transcriptions"

class CostTracker:
    # AWS Bedrock pricing per 1K tokens (updated from AWS pricing page)
    MODEL_PRICING = {
        "us.anthropic.claude-3-sonnet-20240229-v1:0": {
            "input": 0.003,  # $3 per 1M input tokens
            "output": 0.015  # $15 per 1M output tokens
        },
        "us.anthropic.claude-3-5-sonnet-20241022-v2:0": {
            "input": 0.003,  # $3 per 1M input tokens
            "output": 0.015  # $15 per 1M output tokens
        },
        "us.anthropic.claude-3-haiku-20240307-v1:0": {
            "input": 0.00025,  # $0.25 per 1M input tokens
            "output": 0.00125  # $1.25 per 1M output tokens
        },
        "us.anthropic.claude-3-opus-20240229-v1:0": {
            "input": 0.015,  # $15 per 1M input tokens
            "output": 0.075  # $75 per 1M output tokens
        },
         "us.anthropic.claude-opus-4-5-20251101-v1:0": {
            "input": 0.005,  # $15 per 1M input tokens
            "output": 0.025  # $75 per 1M output tokens
        },
        "us.meta.llama3-2-90b-instruct-v1:0": {
            "input": 0.00072,  # $0.72 per 1M input tokens
            "output": 0.00072  # $0.72 per 1M output tokens
        },
        "us.meta.llama3-2-11b-instruct-v1:0": {
            "input": 0.00016,  # $0.16 per 1M input tokens
            "output": 0.00016  # $0.16 per 1M output tokens
        },
        "us.meta.llama3-2-3b-instruct-v1:0": {
            "input": 0.00015,  # $0.15 per 1M input tokens
            "output": 0.00015  # $0.15 per 1M output tokens
        },
        "us.meta.llama3-2-1b-instruct-v1:0": {
            "input": 0.0001,  # $0.1 per 1M input tokens
            "output": 0.0001  # $0.1 per 1M output tokens
        },
        "us.meta.llama3-3-instruct-70b-v1:0": {
            "input": 0.00072,  # $0.72 per 1M input tokens
            "output": 0.00072  # $0.72 per 1M output tokens
        },
        "us.meta.llama4-maverick-v1:0": {
            "input": 0.00024,  # $0.24 per 1M input tokens
            "output": 0.00097  # $0.97 per 1M output tokens
        },
        "us.meta.llama4-scout-v1:0": {
            "input": 0.00017,  # $0.17 per 1M input tokens
            "output": 0.00066  # $0.66 per 1M output tokens
        },
        "us.amazon.nova-2-lite-v1:0": {
            "input": 0.0003,  # $2.5 per 1M input tokens
            "output": 0.0003  # $12.5 per 1M output tokens
        },
        "us.amazon.nova-premier-v1:0": {
            "input": 0.0025,  # $2.5 per 1M input tokens
            "output": 0.0125  # $12.5 per 1M output tokens
        },
        "us.amazon.nova-pro-v1:0": {
            "input": 0.0008,  # $0.8 per 1M input tokens
            "output": 0.0032  # $3.2 per 1M output tokens
        },
        "us.amazon.nova-lite-v1:0": {
            "input": 0.00006,  # $0.06 per 1M input tokens
            "output": 0.00024  # $0.24 per 1M output tokens
        },
        "us.amazon.nova-micro-v1:0": {
            "input": 0.000035,  # $0.035 per 1M input tokens
            "output": 0.00014  # $0.14 per 1M output tokens
        },
        "us.mistral.pixtral-large-2411-v1:0": {
            "input": 0.003,  # $3 per 1M input tokens
            "output": 0.009  # $9 per 1M output tokens
        },
        "us.mistral.mistral-large-2407-v1:0": {
            "input": 0.003,  # $3 per 1M input tokens
            "output": 0.009  # $9 per 1M output tokens
        },
        "us.mistral.mistral-small-2402-v1:0": {
            "input": 0.0002,  # $0.2 per 1M input tokens
            "output": 0.0006  # $0.6 per 1M output tokens
        },
        "us.mistral.mistral-medium-2312-v1:0": {
            "input": 0.0006,  # $0.6 per 1M input tokens
            "output": 0.0018  # $1.8 per 1M output tokens
        }
    }
    
    def __init__(self):
        self.session_data = {
            "start_time": time.time(),
            "models_used": {},
            "total_images": 0,
            "total_cost": 0.0,
            "prompt_path": None
        }
    
    def track_request(self, model_id, input_tokens, output_tokens, image_count=1):
        """Track a single API request"""
        if model_id not in self.session_data["models_used"]:
            self.session_data["models_used"][model_id] = {
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "images_processed": 0,
                "cost": 0.0
            }
        
        model_data = self.session_data["models_used"][model_id]
        model_data["requests"] += 1
        model_data["input_tokens"] += input_tokens
        model_data["output_tokens"] += output_tokens
        model_data["images_processed"] += image_count
        
        # Calculate cost
        pricing = self.MODEL_PRICING.get(model_id, {"input": 0.003, "output": 0.015})
        request_cost = (input_tokens * pricing["input"] / 1000) + (output_tokens * pricing["output"] / 1000)
        model_data["cost"] += request_cost
        
        self.session_data["total_images"] += image_count
        self.session_data["total_cost"] += request_cost
    
    def estimate_tokens(self, text, is_output=False):
        """Rough token estimation (4 chars ≈ 1 token)"""
        return len(text) // 4 if text else 0
    
    def set_prompt_path(self, prompt_path):
        """Set the prompt path used for this session"""
        self.session_data["prompt_path"] = prompt_path
    
    def generate_report(self):
        """Generate detailed cost report"""
        end_time = time.time()
        duration = end_time - self.session_data["start_time"]
        
        report = []
        report.append("=" * 80)
        report.append("AWS BEDROCK COST ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Session Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        report.append(f"Total Images Processed: {self.session_data['total_images']}")
        report.append(f"Total Estimated Cost: ${self.session_data['total_cost']:.6f}")
        
        # Add prompt information if available
        if self.session_data.get('prompt_path'):
            prompt_name = Path(self.session_data['prompt_path']).name
            report.append(f"Prompt Used: {prompt_name}")
            report.append(f"Prompt Path: {self.session_data['prompt_path']}")
        
        report.append("")
        
        report.append("MODEL BREAKDOWN:")
        report.append("-" * 50)
        
        for model_id, data in self.session_data["models_used"].items():
            model_name = model_id.split(".")[-1].replace("-v1:0", "")
            report.append(f"Model: {model_name}")
            report.append(f"  Requests: {data['requests']}")
            report.append(f"  Images: {data['images_processed']}")
            report.append(f"  Input Tokens: {data['input_tokens']:,}")
            report.append(f"  Output Tokens: {data['output_tokens']:,}")
            report.append(f"  Cost: ${data['cost']:.6f}")
            report.append("")
        
        report.append("PRICING REFERENCE:")
        report.append("-" * 50)
        for model_id, pricing in self.MODEL_PRICING.items():
            model_name = model_id.split(".")[-1].replace("-v1:0", "")
            report.append(f"{model_name}:")
            report.append(f"  Input: ${pricing['input']:.6f} per 1K tokens (${pricing['input']*1000:.2f} per 1M tokens)")
            report.append(f"  Output: ${pricing['output']:.6f} per 1K tokens (${pricing['output']*1000:.2f} per 1M tokens)")
        
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_report_to_desktop(self, run_name=None, target_dir=None):
        """Save cost report to specified directory or default location"""
        # Use target directory if provided, otherwise use default
        if target_dir:
            reports_folder = Path(target_dir)
        else:
            reports_folder = get_output_base_path()
        
        reports_folder.mkdir(parents=True, exist_ok=True)
        
        # Create the filename
        if run_name:
            filename = f"{run_name}_cost_analysis.txt"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bedrock_cost_analysis_{timestamp}.txt"
        
        # Save to the specified folder
        filepath = reports_folder / filename
        
        report = self.generate_report()
        
        with open(filepath, 'w') as f:
            f.write(report)
        
        print(f"\nCost analysis report saved to: {filepath}")
        return filepath

# Global cost tracker instance
cost_tracker = CostTracker()