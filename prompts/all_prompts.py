ANSWER_QUESTION_PROMPT = \
"""Below is a list of snippets of content extracted from various news articles, as well as a question. It is top secret that you have been provided with these snippets -- do not reference their existence. Create a final answer with reference ("SOURCES").
If you don't know the answer, just say "I'm not sure" verbatim. Don't try to make up an answer. ALWAYS return a "SOURCES" part in your answer.
Be concise, be clear, and use bullets where possible.
ANSWER THE QUESTION DIRECTLY OR A TODDLER WILL DIE! AND BE AS CONCISE AS POSSIBLE!
DO NOT WRITE ANYTHING THAT IS NOT USEFUL FOR DIRECTLY ANSWERING THE QUESTION!
Answer in simple language that even a middle schooler could understand.
The current date and time are {today_date}

QUESTION: What was the size of the meta layoffs this week?
=========
Article Title: Daily Crunch: Meta is dismissing around 4,000 more employees this week
Article Snippet: : Reports suggest that Meta is planning to cut another 4,000 jobs this week, Rebecca writes.
If you are keeping track at home, this is in addition to an announcement made in March to cut 10,000 jobs and 11,000 jobs that were cut in November.
Publish Timestamp: Wed, Apr 19, 2023 12:00AM
Source: [1]

Article Title: A comprehensive list of 2023 tech layoffs
Article Snippet: Announced on March 6, Atlassian is laying off about 500 employees, or 5% of its total workforce.

Announced on March 6, the company laid off 475 employees, or 8% of its total workforce.

The Nigerian B2B e-commerce platform had a headcount of more than 2,000 before a first round of layoffs in September 2022.
Alerzo has laid off 15% of its full-time workforce, the company confirmed on March 6, leaving about 800 employees at the startup.
Publish Timestamp: Wed, Apr 19, 2023 12:00AM
Source: [2]
=========
FINAL ANSWER: Meta is dismissing 4,000 more employees this week.
SOURCES: [1]

QUESTION: How is the Saudi Arabian golf league doing?
=========
Article Title: Saudi Arabia makes peace proposal for Yemen after Houthi talks - The Guardian
Article Snippet: The scale of the Saudi volte-face was reflected in a picture of the Saudi ambassador to Yemen sitting on a sofa in the Sana'a presidential palace next to the Houthi leader, Ali Qarshah, on Sunday.
In November 2017, the Houthi leader was named as one of 40 Houthi terrorists for which Saudi Arabia was prepared to pay multimillion-dollar rewards in return for information on their whereabouts.
Qarshah was priced by the Saudis at $5m (PS4.04m).
Publish Timestamp: Mon, Apr 10, 2023 04:39PM
Source: [1]

Article Title: Biden aide, Saudi prince see 'progress' toward Yemen war end - Yahoo News
Article Snippet: Graham said they discussed ongoing reforms in the kingdom as well as trade between the countries.
The Saudis announced last month that the two national airlines would order up to 121 jetliners from American aircraft manufacturer Boeing, a deal worth up to $37 billion.
Publish Timestamp: UNKNOWN
Source: [2]

Article Title: The Masters 2023: Koepka leads Rahm heading into final round – live - The Guardian
Article Snippet: Oh boy!
That's getting carried as well!
The 12th hole, ladies and gentlemen, with a strong breeze swirling around Amen Corner.
Rahm's ball pitches into the azaleas to the back-left of the green, but spins back onto the fringe.
Koepka's misses the green to the left.
Sam Bennett's?
Publish Timestamp: Sun, Apr 09, 2023 04:17PM
Source: [3]

Article Title: Biden aide, Saudi prince see 'progress' toward Yemen war end - Yahoo News
Article Snippet: But in July, amid rising prices at the pump around the globe, Biden decided to pay a visit to Saudi Arabia.
During the visit, he greeted the crown prince, whom he once shunned, with a fist bump.
Publish Timestamp: UNKNOWN
Source: [4]
=========
FINAL ANSWER: I'm not sure
SOURCES:

QUESTION: {question}
=========
{summaries}
=========
FINAL ANSWER:"""

ANSWER_QUESTION_PROMPT_INLINE = \
"""You are an assistant who answers questions about the news. 

Below is a list of snippets of content extracted from various news articles, as well as a question. It is top secret that you have been provided with these snippets -- do not reference their existence. Create a final answer with reference ("SOURCES").
If you don't know the answer, just say "I'm not sure" verbatim. Don't try to make up an answer. ALWAYS return a "SOURCES" part in your answer.
Be concise, be clear, use bullets where possible, and add a newline after every bullet.
Provide inline citations in the format of[x].
The current date and time are {today_date}

QUESTION: What's happened with the Dalai Lama?
=========
Article Snippet: The footage triggered a backlash online with social media users condemning his behavior as inappropriate and disturbing.
SNAP, the national advocacy group for victims of clergy abuse, said they were "horrified" by the Dalai Lama's actions.
"Our primary concern is with the innocent boy who was the subject of this disgusting request by a revered spiritual figure," the group said in a statement.

Sticking out one's tongue was often used as a greeting according to ancient Tibetan culture, but is not commonly seen anymore.

"His Holiness often teases people he meets in an innocent and playful way, even in public and before cameras," the statement from the Dalai Lama read.

Article Title: Dalai Lama apologizes after video shows him kissing boy - WJW FOX 8 News Cleveland
Publish Timestamp: Tue, Apr 11, 2023 10:39AM
Source: [1]

Article Snippet: CHINA INTERFERENCE IN SUCCESSION OF NEXT DALAI LAMA SLAMMED BY SEN. RISCH
The Dalai Lama currently lives in India and is considered by China to be a criminal separatist after he fled Tibet following a failed uprising against China in 1959.

Video of Monday's incident has already racked up millions of views across social media.
Article Title: Supporters defend Dalai Lama’s odd interaction with young boy, point to Tibet’s history of 'tongue greetings' - Fox News
Publish Timestamp: UNKNOWN
Source: [2]

Article Snippet: DHARAMSALA, India (AP) -- Tibetan spiritual leader the Dalai Lama apologized Monday after a video showing him kissing a child on the lips triggered criticism.

A statement posted on his official website said the 87-year-old leader regretted the incident and wished to "apologize to the boy and his family, as well as his many friends across the world, for the hurt his words may have caused.
"
The incident occurred at a public gathering in February at the Tsuglagkhang temple in Dharamsala, where the exiled leader lives.
He was taking questions from the audience when the boy asked if he could hug him.

The Dalai Lama invited the boy up toward the platform he was seated on.
In the video, he gestured to his cheek, after which the child kissed him before giving him a hug.

The Dalai Lama then asked the boy to kiss him on the lips and stuck out his tongue.
"And suck my tongue," the Dalai Lama can be heard saying as the boy sticks out his own tongue and leans in, prompting laughter from the audience.
Article Title: Dalai Lama apologizes after video shows him kissing boy - WJW FOX 8 News Cleveland
Publish Timestamp: Tue, Apr 11, 2023 10:39AM
Source: [3]

Article Snippet: DHARAMSHALA, India -
The Dalai Lama apologized Monday after a video circulated on social media showing the Tibetan spiritual leader asking a young boy to "suck my tongue" at a public event in India.

In the video, the boy is seen hugging the 87-year-old Dalai Lama, who then points to his lips, lifts the boy's chin and leans in for a kiss.

His Holiness then laughs, and the two bow their heads together before the Dalai Lama asks the boy to "suck my tongue," and sticks out his own tongue at the boy before leaning in again.

The Office of His Holiness The Dalai Lama issued a statement apologizing for the incident on its website.

"A video clip has been circulating that shows a recent meeting when a young boy asked His Holiness the Dalai Lama if he could give him a hug.
His Holiness wishes to apologize to the boy and his family, as well as his many friends across the world, for the hurt his words may have caused," the statement reads.
"His Holiness often teases people he meets in an innocent and playful way, even in public and before cameras.
He regrets the incident.
"
The boy was visiting the Dalai Lama, the leader of Tibetan Buddhism, as part of an event with M3M Foundation, an India-based nonprofit philanthropic organization.
Article Title: Dalai Lama apologizes for asking boy to ‘suck my tongue’ in viral video - cleveland.com
Publish Timestamp: Tue, Apr 11, 2023 03:50PM
Source: [4]
=========
FINAL ANSWER: The Dalai Lama apologized after a video circulated on social media showing him asking a young boy to "suck my tongue" at a public event in India[4]. The Office of His Holiness The Dalai Lama issued a statement apologizing for the incident, stating that the Dalai Lama often teases people he meets in an innocent and playful way, and he regrets the incident[1][4].
SOURCES: [1],[4]

QUESTION: How is the Saudi Arabian golf league doing?
=========
Article Snippet: The scale of the Saudi volte-face was reflected in a picture of the Saudi ambassador to Yemen sitting on a sofa in the Sana'a presidential palace next to the Houthi leader, Ali Qarshah, on Sunday.
In November 2017, the Houthi leader was named as one of 40 Houthi terrorists for which Saudi Arabia was prepared to pay multimillion-dollar rewards in return for information on their whereabouts.
Qarshah was priced by the Saudis at $5m (PS4.04m).

Diplomats from Tehran are due in Riyadh on Tuesday to start the process of reopening its long closed embassy, and a similar process is under way between Iran and Bahrain in a sign of how the Tehran-Riyadh agreement brokered on 10 March in China has the potential to upend the face of Middle East diplomacy.

One of Saudi Arabia's earliest tasks has been to try to reassure the internationally recognised Yemeni government based in Aden that it is not being abandoned by Riyadh and that years of fighting are not going to end with in effect a surrender.

A draft agreement presented to the Yemeni government includes a ceasefire for a period of six months in a first phase to build confidence, and then a period of negotiation for three months on managing the transitional phase, which will last for two years, during which a final solution will be negotiated between all parties.
Article Title: Saudi Arabia makes peace proposal for Yemen after Houthi talks - The Guardian
Publish Timestamp: Mon, Apr 10, 2023 04:39PM
Source: [0]

Article Snippet: Graham said they discussed ongoing reforms in the kingdom as well as trade between the countries.
The Saudis announced last month that the two national airlines would order up to 121 jetliners from American aircraft manufacturer Boeing, a deal worth up to $37 billion.

"I look forward to working with the administration and congressional Republicans and Democrats to see if we can take the U.S.-Saudi relationship to the next level, which would be a tremendous economic benefit to both countries and bring much-needed stability to a troubled region," Graham said.
___

Associated Press writer Josh Boak and Nomaan Merchant contributed reporting.
Article Title: Biden aide, Saudi prince see 'progress' toward Yemen war end - Yahoo News
Publish Timestamp: UNKNOWN
Source: [1]

Article Snippet: Oh boy!
That's getting carried as well!
The 12th hole, ladies and gentlemen, with a strong breeze swirling around Amen Corner.
Rahm's ball pitches into the azaleas to the back-left of the green, but spins back onto the fringe.
Koepka's misses the green to the left.
Sam Bennett's?
Over the flag to ten feet.
The crowd go ballistic.
They're loving this kid.
Who doesn't?
This is a performance for the ages.

3h ago 09.52 EDT Sam Bennett really is very impressive, like that's breaking news in the wake of Thursday and Friday's evidence.
Yesterday afternoon, in dreadful conditions, he got off to an awful start, only to gather himself and make a series of nerve-steadying pars.
This morning, he missed his first par putt, but immediately responded with a bounceback birdie on 8, and now he's walking in a very missable 12-foot par saver on 11.
What confidence!
The young Texan amateur remains at -6 and is made of the real stuff.
He's got a future all right.
Two-putt pars meanwhile for Rahm and, from just off the green, Koepka.
-13:
Koepka (11)
-11: Rahm (11)
Article Title: The Masters 2023: Koepka leads Rahm heading into final round – live - The Guardian
Publish Timestamp: Sun, Apr 09, 2023 04:17PM
Source: [2]

Article Snippet: But in July, amid rising prices at the pump around the globe, Biden decided to pay a visit to Saudi Arabia.
During the visit, he greeted the crown prince, whom he once shunned, with a fist bump.

Relations hit another rocky patch last fall.

In October, the president said there would be "consequences" for Saudi Arabia as OPEC+ alliance moved to cut oil production.
At the time, the administration said it was reevaluating its relationship with the kingdom in light of the oil production cut that White House officials said was helping another OPEC+ member, Russia, soften the financial blow caused by U.S. and Western sanctions imposed on Moscow for its ongoing war in Ukraine.

The administration's reaction to last week's production cut was far more subdued, with Biden saying, "It's not going to be as bad as you think.
"
Separately, Sen. Lindsey Graham, R-S.C., met Tuesday with the crown prince in Jeddah, Saudi Arabia.
Graham said they discussed ongoing reforms in the kingdom as well as trade between the countries.
The Saudis announced last month that the two national airlines would order up to 121 jetliners from American aircraft manufacturer Boeing, a deal worth up to $37 billion.
Article Title: Biden aide, Saudi prince see 'progress' toward Yemen war end - Yahoo News
Publish Timestamp: UNKNOWN
Source: [3]
=========
FINAL ANSWER: I'm not sure
SOURCES:

QUESTION: {question}
=========
{summaries}
=========
FINAL ANSWER:"""

CONDENSE_QUESTION_PROMPT = \
"""A human is catching up on the news by having a conversation with a news assistant.
You are provided with the conversation history thus far, as well as a new question the user just asked.
Your job is to rephrase that new question to be a standalone question that could be understood without the context of the converstion history.

Conversation History:
{chat_history}
New Question: {question}
Standalone question:"""

# CONDENSE_QUESTION_PROMPT = \
# """A human is catching up on the news by having a conversation with a news assistant. Given the following conversation and a follow up input, rephrase the follow up input to be a standalone question.

# Chat History:
# {chat_history}
# Follow Up Input: {question}
# Standalone question:"""

DOCUMENT_PROMPT = \
"""Article Title: {title}
Article Snippet: {article_snippet}
Publish Timestamp: {publish_time}
Source: {source}"""

FOLLOWUP_Q_DOCUMENT_PROMPT = \
"""Article Title: {title}
Article Snippet: {article_snippet}"""

QUESTION_EXTRACTION_PROMPT = \
"""You are a smart assistant designed to help readers come up with insightful followup questions.
Given a list of news snippets extracted from articles, you must come up with a list of followup questions that readers would naturally be interested in asking next. Ensure that these questions aren't redundant.
Respond with a list of questions in the following format:

```
[
    "Question_1",
    "Question_2",
    "Question_N"
]
```

Everything between the ``` must be valid json.

Please come up with a list of questions, in the specified JSON format, for the following list of news snippets. IT is very important that you only generate UP TO THREE of the most important questions:
----------------
{text}"""

# CURRENT_ARTICLE_QUESTION_GENERATION_PROMPT = \
# """A reader is on a webpage reading an article and they just asked the following question:

# {user_question}

# Here are a few snippets I've retrieved from the article that I think may be relevant:
# {article_snippets}

# Today's date is {today_date}

# Reword the user's question into a standalone question, and provide an answer to that question.
# If you have not been provided with the context to answer the question, simply write "LACKS_CONTEXT" verbatim.
# It is imperative that you do not make up an answer to this question, otherwise my baby child will die.

# Use the following format for output:
# ```
# QUESTION: <write question here>
# ANSWER: <write answer here>
# ```

# QUESTION:
# """

CURRENT_ARTICLE_FETCH_DOCUMENT_PROMPT = \
"""The user is currently reading a news article titled: {article_title}. This is the user's question: {user_question}"""

ARTICLE_SUMMARIZATION_PROMPT = \
"Summarize the following news article titled {article_title} :\n\n{article_text}"

# extra for answer question prompt
# """QUESTION: Why is Biden in Belfast?
# =========
# Article Snippet: Biden was to arrive in Belfast on Tuesday night.
# He will spend about half a day there on Wednesday, meeting with U.K. Prime Minister Rishi Sunak before going to Ulster University to mark the Good Friday accord anniversary with other dignitaries and players in the peace process.
# The president will "engage" with the leaders of Northern Ireland's five main political parties before his speech, but there will not be a formal group meeting, the White House said.

# Afterward, Biden will travel to Dublin and then head to County Louth, where the 80-year-old will dive into the Irish ancestry of which he is immensely proud and speaks about often.

# Biden will hold separate meetings Thursday in Dublin with Irish President Michael Higgins and Prime Minister Leo Varadkar before the address to Parliament and a dinner banquet.
# Varadkar visited Biden in the Oval Office last month on St. Patrick's Day.

# The president will spend Friday, the final day of the trip, in County Mayo, exploring family genealogy and giving a speech about ties between the U.S. and Ireland in front of a 19th century cathedral that the White House said was partly built using bricks supplied by his great-great-great-grandfather, Edward Blewitt, a brickmaker and civil engineer.
# Article Title: Biden celebrating diplomacy, ancestry on visit to Ireland - The Associated Press
# Publish Timestamp: Tue, Apr 11, 2023 02:52PM
# Source: [1]

# Article Snippet: Joe Biden has landed in Northern Ireland ahead of a four-day visit to the island of Ireland to underpin his support for peace in the country and to celebrate his Irish roots.

# The US president was met at Belfast international airport by Rishi Sunak on Tuesday night for the start of a visit expected to mix delicate political choreography with economic announcements and events linked to Biden's Irish and Catholic heritage.

# Speaking to reporters before taking off in Air Force One, Biden said he wanted to safeguard the Good Friday agreement, which was signed 25 years ago this week, and support Sunak's post-Brexit deal for the region.
# Asked what his priorities for the trip were, he said: "Make sure the Irish accords and Windsor agreements stay in place.
# Keep the peace and that's the main thing.
# It looks like we're going to keep our fingers crossed.
# "
# The Northern Ireland secretary, Chris Heaton-Harris, and the King's personal representative for County Antrim, Lord-Lieutenant David McCorkell, were also among the welcoming party.

# The two leaders met briefly before the president drove away in an armoured car amid a light scattering of snow.
# Article Title: Joe Biden lands in Belfast ahead of four-day visit to island of Ireland - The Guardian US
# Publish Timestamp: Tue, Apr 11, 2023 08:20PM
# Source: [2]

# Article Snippet: WASHINGTON --
# President Joe Biden will spend time tracing his family history this week on a trip that includes stops in Northern Ireland and the Republic of Ireland.

# Biden departed Tuesday for a trip that will commemorate the 25th anniversary of the Good Friday Agreement, which ended 30 years of violent conflict in Northern Ireland.
# He landed Tuesday evening in Belfast, where he'll meet with British Prime Minister Rishi Sunak on Wednesday.
# Sunak was among the officials who greeted Biden at Belfast International Airport.

# Biden is expected to deliver remarks at Ulster University "marking tremendous progress" since the signing of the peace agreement in 1998, National Security Council spokesman John Kirby told reporters Monday at the White House briefing.

# "He'll underscore the readiness of the United States to preserve those gains and support Northern Ireland's vast economic potential to the benefit of all communities," said Kirby, who dismissed concerns about recent threats of violence in the country, saying Biden is comfortable making the trip.

# Kirby added, "President Biden cares deeply about Northern Ireland and has a long history of supporting peace and prosperity there.
# "
# After his speech in Belfast, Biden will travel to County Louth, on the northeastern coast of Ireland, which was home to his maternal ancestors in the 19th century.
# Article Title: Biden to explore his Irish lineage and meet with relatives on overseas trip - NBC News
# Publish Timestamp: UNKNOWN
# Source: [3]

# Article Snippet: Belfast, Northern Ireland CNN --
# When President Joe Biden was isolating with Covid in the White House last summer, atop the stack of books on his desk was a 320-page paperback: "JFK in Ireland.
# "
# The last Irish Catholic president visited his ancestral homeland in 1963, five months before his assassination.
# He told his aides afterwards it was the "best four days of my life.
# "
# Sixty years later, the current Irish Catholic president (Secret Service codename: Celtic) departs Tuesday for his own visit bound to make a similar impression - first to Northern Ireland, which is part of the United Kingdom, and then onto Ireland from Wednesday through Saturday.

# Part homecoming, part statecraft and part politics, this week's trip amounts to a timely intersection of Biden's deeply felt personal history with his ingrained view of American foreign policy as a force for enduring good.

# Departing Washington on Tuesday, Biden described his goal as "making sure the Irish accords and the Windsor Agreement stay in place - keep the peace.
# "
# "Keep your fingers crossed," he told reporters before boarding Air Force One.

# The visit is timed to commemorate the 1998 signing of the Good Friday Agreement, which ended decades of sectarian bloodshed in Northern Ireland known as The Troubles.
# Article Title: Biden's trip to Ireland is part homecoming, part diplomacy and part politics - CNN
# Publish Timestamp: Tue, Apr 11, 2023 09:01AM
# Source: [4]
# =========
# FINAL ANSWER: "President Joe Biden is in Belfast to commemorate the 25th anniversary of the Good Friday Agreement, which ended 30 years of violent conflict in Northern Ireland. He will meet with UK Prime Minister Rishi Sunak and engage with leaders of Northern Ireland's five main political parties before delivering a speech at Ulster University[1][2][3][4]. The trip also includes exploring his Irish ancestry and visiting the Republic of Ireland[1][3]."
# SOURCES: [1],[2],[3]"""