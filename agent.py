"""Visual branding subgraph with branding, storefront, and menu generation nodes."""

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState,START, END
from langgraph.runtime import Runtime
from langchain.chat_models import init_chat_model
from configuration import Context


class Input(MessagesState):
    """Input for visual menu generation."""



class VisualBrandingState(MessagesState):
    """State for visual branding generation workflow."""
    # Input from restaurant research
    restaurant_name: str = Field(default="", description="The name of the restaurant")
    cuisine: str = Field(default="", description="The type of cuisine the restaurant serves")
    location: str = Field(default="", description="The location of the restaurant")
    target_audience: str = Field(default="", description="The target audience for the restaurant")
    budget_range: str = Field(default="", description="The budget range for the restaurant")
    report_parsed: bool = Field(default=False, description="Has the report been parsed?")

    # Generated menu assets
    menu_text: str = Field(default="", description="the text on the menu")
    feedback_on_menu_content: str = Field(default="", description="Feedback on the menu content")
    menu_content_approved: bool = Field(default=False, description="Is the menu text approved?")
    menu_image_response_id: str = Field(default="", description="The response ID of the generated menu image")
    menu_image_feedback: str = Field(default="", description="Feedback on the menu image")
    menu_image_approved: bool = Field(default=False, description="Is the menu image approved?")
    feedback_on_menu_image: str = Field(default="", description="Feedback on the menu image")


async def parse_report(state: VisualBrandingState):
    """Parse the report and update the state"""
    class Report(BaseModel):
        restaurant_name: str
        cuisine: str
        location: str
        budget_range: str

    model = ChatAnthropic(model="claude-sonnet-4-20250514")
    
    system_prompt = """Please parse this report and return the restaurant name, 
cuisine, location and budget range. If the report already has menu items then please store those in the cuisine field as a string of items.
"""

    # Get the user message from the messages state
    user_message = state["messages"][-1]
    
    response = await model.with_structured_output(Report).ainvoke([
        SystemMessage(content=system_prompt),
        user_message
    ])

    return {
        "restaurant_name": response.restaurant_name,
        "cuisine": response.cuisine,
        "location": response.location,
        "budget_range": response.budget_range,
        "report_parsed": True
    }

async def menu_content_agent(state: VisualBrandingState, runtime: Runtime[Context]):
    """Generate the menu content"""

    model = init_chat_model(runtime.context.menu_text_model)

    system_prompt = runtime.context.menu_text_prompt.format(
        restaurant_name=state.get("restaurant_name", ""),
        cuisine=state.get("cuisine", ""),
        location=state.get("location", ""),
        budget_range=state.get("budget_range", ""),
        menu_text=state.get("menu_text", "")
    )

    if state.get("feedback_on_menu_content", "") != "":
        messages = [SystemMessage(content=system_prompt), state.get("feedback_on_menu_content", "")]
    else:
        messages = [SystemMessage(content=system_prompt)]
    
    response = await model.ainvoke(messages)
    
    return {
        "messages": response,
        "menu_text": response.content,
        "menu_content_approved": False
    }

async def menu_content_approval(state: VisualBrandingState):
    """Check if the menu content is approved"""
    class MenuContentApproval(BaseModel):
        menu_content_approved: bool = Field(default=False, description="Is the menu content approved by the user?")
        feedback_on_menu_content: str = Field(default="", description="Feedback on the menu content")
    
    model = ChatAnthropic(model="claude-sonnet-3-7-sonnet-latest")

    system_prompt = """You are a helpful assistant that checks if the menu content is approved by the user, if not what feedback did they user provide?
    """

    response = await model.with_structured_output(MenuContentApproval).ainvoke([
        SystemMessage(content=system_prompt), state.messages[-1]
    ])

    if response.menu_content_approved == True:
        return {"menu_content_approved": True}
    else:
        return {"feedback_on_menu_content": response.feedback_on_menu_content}

async def menu_image_feedback_reader(state: VisualBrandingState):
    """Check if the menu image is approved"""
    class MenuImageApproval(BaseModel):
        feedback_on_menu_image: str = Field(default="", description="Feedback on the menu image")
    
    model = ChatAnthropic(model="claude-sonnet-3-7-sonnet-latest")

    system_prompt = """You are a helpful assistant that checks if any feedback was provided on the menu image by the user, if so what is it?
    """

    response = await model.with_structured_output(MenuImageApproval).ainvoke([
        SystemMessage(content=system_prompt), state.messages[-1]
    ])

    return {"feedback_on_menu_image": response.feedback_on_menu_image}

async def menu_image_agent(state: VisualBrandingState):
    """Generate restaurant brand concept and logo."""
    
    tool = { "type": "image_generation" }
    if state.get("menu_image_response_id", "") != "":
        model = ChatOpenAI(model="gpt-5", output_version="responses/v1", previous_response_id=state.get("menu_image_response_id", "")).bind_tools([tool])
    else:
        model = ChatOpenAI(model="gpt-5", output_version="responses/v1").bind_tools([tool])

    
    system_prompt = f"""You are an expert menu designer and culinary consultant with extensive experience in creating comprehensive, 
well-structured restaurant menus. Your specialty is translating restaurant concepts
into compelling visual menus that drive sales and enhance the dining experience.

Here's the menu content:
<menu_content>
{state.get("menu_text", "")}
</menu_content>

Use your image generation tool to generate a visual menu!"""
    
    if state.get("feedback_on_menu_image", "") != "":
        messages = [SystemMessage(content=system_prompt), state.get("feedback_on_menu_image", "")]
    else:
        messages = [SystemMessage(content=system_prompt)]
    
    response = await model.ainvoke(messages)

    
    return {
        "messages": response,
        "menu_image_response_id": response.id
    }

# conditional edge to determine whether to parse the report or generate the menu
async def router(state: VisualBrandingState):
    """Parse the report and generate the menu"""
    if state.get("report_parsed", False) == False:
        return "parse_report"
    # menu hasn't been approved yet, let's check it.
    elif state.get("menu_content_approved", False) == False:
        return "menu_content_approval"
    # otherwise we're in the menu image generation phase so allow let's extract feedback from the user, and continue to generate the menu image.
    else:
        return "menu_image_feedback_reader"

# conditional edge to determine whether to go to END or continue to the image generation phase.
async def menu_content_approval_router(state: VisualBrandingState):
    """Check if the menu content is approved"""
    if state.get("menu_content_approved", False) == True:
        return "menu_image_agent"
    else:
        return "menu_content_agent"
    

# Build the visual branding subgraph
graph = StateGraph(state_schema=VisualBrandingState, input_schema=Input, context_schema=Context)

# Add nodes
graph.add_node("parse_report", parse_report)
graph.add_node("menu_content_agent", menu_content_agent)
graph.add_node("menu_image_agent", menu_image_agent)
graph.add_node("menu_image_feedback_reader", menu_image_feedback_reader)
graph.add_node("menu_content_approval", menu_content_approval)

graph.add_conditional_edges(
    START,
    # Function representing our conditional edge
    router,
    {
        # If we want to generate the menu, we go to the generate_menu node.
        "parse_report": "parse_report",
        "menu_content_agent": "menu_content_agent",
        "menu_content_approval": "menu_content_approval",
        "menu_image_feedback_reader": "menu_image_feedback_reader",
        "menu_image_agent": "menu_image_agent",
        "parse_report": "parse_report"
    },
)

graph.add_conditional_edges(
    "menu_content_approval",
    menu_content_approval_router,
    {
        "menu_image_agent": "menu_image_agent",
        "menu_content_agent": "menu_content_agent"
    }
)

graph.add_edge("parse_report", "menu_content_agent")
graph.add_edge("menu_image_feedback_reader", "menu_image_agent")
graph.add_edge("menu_image_agent", END)


# Compile the subgraph
compiled_graph = graph.compile()