from reranker import score_candidates

claim = "500 rupee notes will be banned from ATMs, RBI issued order"

candidates = [
    ("SAME (en)",      {"title": "No, RBI Will Not 'Stop' Dispensing Rs 500 Notes From ATMs",
                        "claim": "RBI has asked all banks to stop disbursing 500₹ notes by 30 sep from ATM."}),
    ("SAME (hi)",      {"title": "आरबीआई ने एटीएम से 500 रुपये के नोट बंद करने का आदेश नहीं दिया",
                        "claim": "आरबीआई ने एटीएम से 500 रुपये के नोट बंद करने का आदेश दिया है"}),
    ("SAME (pa)",      {"title": "ਆਰਬੀਆਈ ਨੇ ਏਟੀਐਮ ਤੋਂ 500 ਰੁਪਏ ਦੇ ਨੋਟ ਬੰਦ ਕਰਨ ਦਾ ਹੁਕਮ ਨਹੀਂ ਦਿੱਤਾ",
                        "claim": "ਆਰਬੀਆਈ ਨੇ ਏਟੀਐਮ ਤੋਂ 500 ਰੁਪਏ ਦੇ ਨੋਟ ਬੰਦ ਕਰਨ ਦਾ ਹੁਕਮ ਦਿੱਤਾ ਹੈ"}),
    ("RELATED",        {"title": "The Government of India has not released a ₹500 note featuring Netaji",
                        "claim": "A new ₹500 currency note bearing the image of Netaji Subhas Chandra Bose has been officially released."}),
    ("RELATED",        {"title": "RBI has not launched new ₹500 plastic notes",
                        "claim": "RBI has launched new ₹500 plastic currency notes without Mahatma Gandhi's photograph."}),
    ("UNRELATED",      {"title": "Hot lemon water does not cure cancer",
                        "claim": "Drinking hot water with lemon every morning cures cancer."}),
    ("UNRELATED",      {"title": "5G network did not cause the second wave of Covid-19",
                        "claim": "5G towers spread coronavirus."}),
]

scores = score_candidates(claim, [c for _, c in candidates])
for (label, c), s in sorted(zip(candidates, scores), key=lambda x: -x[1]):
    print(f"{s:.3f}  {label:10}  {c['title'][:60]}")