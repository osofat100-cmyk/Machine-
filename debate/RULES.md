# Debate rules

Question: which premade, fully done system should the user run for PEARL (BigONE PEARL-USDT, Coinbase PEARL-USD)?

Speakers (the same six agents who did the research):
- Agent 1 - GitHub / GitLab
- Agent 2 - Papers With Code / arXiv
- Agent 3 - PyPI / npm / HuggingFace / Docker Hub
- Agent 4 - Kaggle / Colab
- Agent 5 - Freqtrade / Hummingbot / QuantConnect / Backtrader communities
- Agent 6 - SSRN / Google Scholar / ResearchGate

1. Use what you found yourself and what the others wrote in findings_agent*.md. Do not start new research.
2. A web search is allowed ONLY to answer a question someone asked in transcript.md. Say what you searched and what it showed.
3. Only premade, fully done systems. If a pick needs changes, say exactly which ones (the user must approve any change).
4. Reply to the others by name. Quote what they said when you disagree.
5. Max 200 words per message.
6. Write your own message into transcript.md yourself (command below). Nobody else edits your words.

Append command (replace N and the text):
    flock /home/user/Machine-/debate/.lock -c 'cat >> /home/user/Machine-/debate/transcript.md' <<'MSG'

    ### Agent N - round R
    your message
    MSG

7. If your own write to transcript.md is blocked, return your message text exactly. The coordinator pastes it unchanged under your heading, marked "(pasted by coordinator, write was blocked)".
