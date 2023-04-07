ANSWER_QUESTION_PROMPT = \
"""Below is a list of snippets of content extracted from various news articles, as well as a question. Create a final answer with reference ("SOURCES").
If you don't know the answer, just say that you don't know. Don't try to make up an answer. ALWAYS return a "SOURCES" part in your answer.
Be concise, be clear, and use bullets where possible.
The current date and time are {today_date}

QUESTION: Which state/country's law governs the interpretation of the contract?
=========
Content: This Agreement is governed by English law and the parties submit to the exclusive jurisdiction of the English courts in  relation to any dispute (contractual or non-contractual) concerning this Agreement save that either party may apply to any court for an  injunction or other relief to protect its Intellectual Property Rights.
Source: 28-pl
Content: No Waiver. Failure or delay in exercising any right or remedy under this Agreement shall not constitute a waiver of such (or any other)  right or remedy.

11.7 Severability. The invalidity, illegality or unenforceability of any term (or part of a term) of this Agreement shall not affect the continuation  in force of the remainder of the term (if any) and this Agreement.

11.8 No Agency. Except as expressly stated otherwise, nothing in this Agreement shall create an agency, partnership or joint venture of any  kind between the parties.

11.9 No Third-Party Beneficiaries.
Publish Timestamp: Monday May 03, 2021 04:37pm
Source: 30-pl
Content: (b) if Google believes, in good faith, that the Distributor has violated or caused Google to violate any Anti-Bribery Laws (as  defined in Clause 8.5) or that such a violation is reasonably likely to occur,
Publish Timestamp: Wednesday May 05, 2021 02:19am
Source: 4-pl
=========
FINAL ANSWER: This Agreement is governed by English law.
SOURCES: 28-pl

QUESTION: What did the president say about Michael Jackson?
=========
Content: Madam Speaker, Madam Vice President, our First Lady and Second Gentleman. Members of Congress and the Cabinet. Justices of the Supreme Court. My fellow Americans.  

Last year COVID-19 kept us apart. This year we are finally together again. 

Tonight, we meet as Democrats Republicans and Independents. But most importantly as Americans. 

With a duty to one another to the American people to the Constitution. 

And with an unwavering resolve that freedom will always triumph over tyranny. 

Six days ago, Russia’s Vladimir Putin sought to shake the foundations of the free world thinking he could make it bend to his menacing ways. But he badly miscalculated. 

He thought he could roll into Ukraine and the world would roll over. Instead he met a wall of strength he never imagined. 

He met the Ukrainian people. 

From President Zelenskyy to every Ukrainian, their fearlessness, their courage, their determination, inspires the world. 

Groups of citizens blocking tanks with their bodies. Everyone from students to retirees teachers turned soldiers defending their homeland.
Publish Timestamp: Tuesday Feb 07, 2023 09:00pm
Source: 0-pl
Content: And we won’t stop. 

We have lost so much to COVID-19. Time with one another. And worst of all, so much loss of life. 

Let’s use this moment to reset. Let’s stop looking at COVID-19 as a partisan dividing line and see it for what it is: A God-awful disease.  

Let’s stop seeing each other as enemies, and start seeing each other for who we really are: Fellow Americans.  

We can’t change how divided we’ve been. But we can change how we move forward—on COVID-19 and other issues we must face together. 

I recently visited the New York City Police Department days after the funerals of Officer Wilbert Mora and his partner, Officer Jason Rivera. 

They were responding to a 9-1-1 call when a man shot and killed them with a stolen gun. 

Officer Mora was 27 years old. 

Officer Rivera was 22. 

Both Dominican Americans who’d grown up on the same streets they later chose to patrol as police officers. 

I spoke with their families and told them that we are forever in debt for their sacrifice, and we will carry on their mission to restore the trust and safety every community deserves.
Publish Timestamp: Tuesday Feb 07, 2023 09:00pm
Source: 24-pl
Content: And a proud Ukrainian people, who have known 30 years  of independence, have repeatedly shown that they will not tolerate anyone who tries to take their country backwards.  

To all Americans, I will be honest with you, as I’ve always promised. A Russian dictator, invading a foreign country, has costs around the world. 

And I’m taking robust action to make sure the pain of our sanctions  is targeted at Russia’s economy. And I will use every tool at our disposal to protect American businesses and consumers. 

Tonight, I can announce that the United States has worked with 30 other countries to release 60 Million barrels of oil from reserves around the world.  

America will lead that effort, releasing 30 Million barrels from our own Strategic Petroleum Reserve. And we stand ready to do more if necessary, unified with our allies.  

These steps will help blunt gas prices here at home. And I know the news about what’s happening can seem alarming. 

But I want you to know that we are going to be okay.
Publish Timestamp: Tuesday Feb 07, 2023 09:00pm
Source: 5-pl
Content: More support for patients and families. 

To get there, I call on Congress to fund ARPA-H, the Advanced Research Projects Agency for Health. 

It’s based on DARPA—the Defense Department project that led to the Internet, GPS, and so much more.  

ARPA-H will have a singular purpose—to drive breakthroughs in cancer, Alzheimer’s, diabetes, and more. 

A unity agenda for the nation. 

We can do this. 

My fellow Americans—tonight , we have gathered in a sacred space—the citadel of our democracy. 

In this Capitol, generation after generation, Americans have debated great questions amid great strife, and have done great things. 

We have fought for freedom, expanded liberty, defeated totalitarianism and terror. 

And built the strongest, freest, and most prosperous nation the world has ever known. 

Now is the hour. 

Our moment of responsibility. 

Our test of resolve and conscience, of history itself. 

It is in this moment that our character is formed. Our purpose is found. Our future is forged. 

Well I know this nation.
Source: Publish Timestamp: Tuesday Feb 07, 2023 09:00pm
Source: 34-pl
=========
FINAL ANSWER: The president did not mention Michael Jackson.
SOURCES:

QUESTION: {question}
=========
{summaries}
=========
FINAL ANSWER:"""

CONDENSE_QUESTION_PROMPT = \
"""A human is catching up on the news by having a conversation with a news assistant. Given the following conversation and a follow up input, rephrase the follow up input to be a standalone question.

Chat History:
{chat_history}
Follow Up Input: {question}
Standalone question:"""

DOCUMENT_PROMPT = \
"""Article Snippet: {article_snippet}
Article Title: {title}
Publish Timestamp: {publish_time}
Source: {source}"""