#!/usr/bin/env python3
"""Ask the AI about things that happened after 2023 to check it cannot remember the test period. -> probe_memory.txt"""
import os

from llama_cpp import Llama

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS = [
    "What is the last month and year you have information about?",
    "Who won the 2024 United States presidential election?",
    "What was Microsoft's stock price at the end of 2024?",
    "What was Microsoft's stock price at the end of 2025?",
    "Did Microsoft stock go up or down in 2024, and by how much?",
    "What happened to Nvidia's stock in 2024?",
    "Which company became the world's most valuable company in 2024?",
    "What did the Federal Reserve do with interest rates in September 2024?",
    "What happened to the stock market in April 2025?",
    "What was Microsoft's revenue for its fiscal year 2025?",
]


def main():
    llm = Llama(model_path=os.path.join(HERE, "models", "Llama-3.2-3B-Instruct-Q4_K_M.gguf"), n_ctx=2048,
                n_threads=4, seed=0, verbose=False)
    lines = []
    for q in QUESTIONS:
        r = llm.create_chat_completion(messages=[{"role": "user", "content": q}], temperature=0.0, max_tokens=80, seed=0)
        a = r["choices"][0]["message"]["content"].strip().replace("\n", " ")
        lines += [f"Q: {q}", f"A: {a}", ""]
        print(lines[-3], "\n", lines[-2], flush=True)
    with open(os.path.join(HERE, "probe_memory.txt"), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
