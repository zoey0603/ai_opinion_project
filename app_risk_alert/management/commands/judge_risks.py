from django.core.management.base import BaseCommand

from app_risk_alert.views import MAX_OLLAMA_TIMEOUT, OLLAMA_TIMEOUT, TOOLS, _build_tool_result


class Command(BaseCommand):
    help = "Use Ollama to gradually fill cached risk judgements without blocking the web page."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of new Ollama judgements to run. Use 0 for no limit.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=OLLAMA_TIMEOUT,
            help="Timeout seconds for each Ollama request.",
        )
        parser.add_argument(
            "--tool",
            choices=TOOLS + ["ALL"],
            default="ALL",
            help="Tool to process.",
        )
        parser.add_argument(
            "--retry-fallback",
            action="store_true",
            help="Re-run existing fallback judgements with Ollama.",
        )

    def handle(self, *args, **options):
        limit = max(0, int(options["limit"]))
        timeout = max(5, min(int(options["timeout"]), MAX_OLLAMA_TIMEOUT))
        tools = TOOLS if options["tool"] == "ALL" else [options["tool"]]
        budget = {"remaining": limit} if limit else None

        limit_label = "no limit" if budget is None else str(limit)
        self.stdout.write(f"Start Ollama risk judgement: tools={','.join(tools)}, limit={limit_label}, timeout={timeout}s")
        for tool in tools:
            before = budget["remaining"] if budget is not None else None
            result = _build_tool_result(
                tool,
                use_ai=True,
                save_result=False,
                ollama_budget=budget,
                ollama_timeout=timeout,
                retry_fallback=options["retry_fallback"],
            )
            used = result["ollama_count"] if budget is None else before - budget["remaining"]
            self.stdout.write(
                f"{tool}: used={used}, candidates={result['candidate_count']}, "
                f"risk={result['risk_count']}, score={result['risk_score']}"
            )
            if budget is not None and budget["remaining"] <= 0:
                break

        remaining = "no limit" if budget is None else str(budget["remaining"])
        self.stdout.write(self.style.SUCCESS(f"Done. Remaining budget={remaining}"))
