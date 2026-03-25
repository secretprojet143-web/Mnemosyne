import re
from typing import Dict, List, Any


class SecurityScanService:
    def __init__(self):
        self.patterns = {
            "api_key_like": [
                r"\bsk-[A-Za-z0-9_\-]{16,}\b",
                r"\b[A-Za-z0-9]{24,}\b"
            ],
            "bearer_token": [
                r"bearer\s+[A-Za-z0-9\-\._~\+/]+=*"
            ],
            "env_secret": [
                r"\b(API_KEY|SECRET|TOKEN|PASSWORD)\s*=\s*[^\s]+"
            ],
            "aws_key_like": [
                r"\bAKIA[0-9A-Z]{16}\b"
            ],
            "password_like": [
                r"\bpassword\s*[:=]\s*[^\s]+"
            ]
        }

    def scan_text(self, text: str) -> Dict:
        findings = []

        if not text:
            return {
                "has_sensitive_data": False,
                "finding_count": 0,
                "findings": []
            }

        for category, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                    findings.append({
                        "category": category,
                        "match": match.group(0),
                        "start": match.start(),
                        "end": match.end()
                    })

        return {
            "has_sensitive_data": len(findings) > 0,
            "finding_count": len(findings),
            "findings": findings
        }

    def redact_text(self, text: str) -> Dict:
        scan = self.scan_text(text)
        redacted = text

        findings_sorted = sorted(scan["findings"], key=lambda x: len(x["match"]), reverse=True)

        for finding in findings_sorted:
            redacted = redacted.replace(finding["match"], "[REDACTED]")

        return {
            "original_has_sensitive_data": scan["has_sensitive_data"],
            "finding_count": scan["finding_count"],
            "redacted_text": redacted,
            "findings": scan["findings"]
        }

    def scan_structured_output(self, data: Any) -> Dict:
        findings = []

        def walk(value, path="root"):
            if isinstance(value, str):
                result = self.scan_text(value)
                if result["has_sensitive_data"]:
                    for finding in result["findings"]:
                        findings.append({
                            "path": path,
                            "category": finding["category"],
                            "match": finding["match"]
                        })
            elif isinstance(value, dict):
                for k, v in value.items():
                    walk(v, f"{path}.{k}")
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    walk(v, f"{path}[{i}]")

        walk(data)

        return {
            "has_sensitive_data": len(findings) > 0,
            "finding_count": len(findings),
            "findings": findings
        }

    def redact_structured_output(self, data: Any) -> Any:
        if isinstance(data, str):
            return self.redact_text(data)["redacted_text"]
        if isinstance(data, dict):
            return {k: self.redact_structured_output(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.redact_structured_output(v) for v in data]
        return data
