from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool

load_dotenv()

# Give the researcher a web search tool
search_tool = SerperDevTool()

# Agent 1 — now has real web search capability
researcher = Agent(
    role="Researcher",
    goal="Research a topic using real web data and return key facts",
    backstory="""You are an expert researcher. 
    You search the web to find current, accurate information 
    and return the most important facts as bullet points.""",
    tools=[search_tool],
    verbose=True
)

# Agent 2 — same as before
writer = Agent(
    role="Writer",
    goal="Take research bullet points and write a short, clear paragraph",
    backstory="""You are a professional writer. 
    You take raw research notes and turn them into 
    a clean, easy-to-read paragraph for a general audience.""",
    verbose=True
)

# Task 1 — updated prompt
research_task = Task(
    description="Search the web and find 3 specific, current ways that small businesses are benefiting from AI agents in 2026. Focus on real examples and measurable results.",
    expected_output="3 bullet points with specific, current examples of small businesses benefiting from AI agents",
    agent=researcher
)

# Task 2 — updated prompt
write_task = Task(
    description="Using the research bullet points provided, write a single clear paragraph explaining to a small business owner why they should consider using AI agents and what they could gain.",
    expected_output="One persuasive but honest paragraph for a small business owner explaining the benefits of AI agents",
    agent=writer
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    verbose=True
)

result = crew.kickoff()
print("\n--- FINAL OUTPUT ---")
print(result)