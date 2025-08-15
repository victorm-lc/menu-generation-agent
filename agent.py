"""Visual branding subgraph with branding, storefront, and menu generation nodes."""

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState,START, END



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

    # Generated menu assets
    menu_image_response_id: str = Field(default="", description="The response ID of the generated menu image")
    menu_text: str = Field(default="", description="the text on the menu")


async def parse_report(state: VisualBrandingState):
    """Parse the report and update the state"""
    class Report(BaseModel):
        restaurant_name: str
        cuisine: str
        location: str
        target_audience: str
        budget_range: str

    model = ChatOpenAI(model="gpt-5")
    
    system_prompt = """Please parse this report and return the restaurant name, 
cuisine, location, target audience and budget range. If the report already has menu items then please store those in the cuisine field as a string of items.
"""

    # Get the first user message from the messages state
    user_message = state["messages"][-1]
    
    response = await model.with_structured_output(Report).ainvoke([
        SystemMessage(content=system_prompt),
        user_message
    ])

    return {
        "restaurant_name": response.restaurant_name,
        "cuisine": response.cuisine,
        "location": response.location,
        "target_audience": response.target_audience,
        "budget_range": response.budget_range
    }


async def menu_agent(state: VisualBrandingState):
    """Generate restaurant brand concept and logo."""
    
    tool = { "type": "image_generation" }
    # if we have a previous menu image, use it as context to generate the menu
    if state.get("menu_image_response_id", "") != "":
        model = ChatOpenAI(model="gpt-5", output_version="responses/v1", previous_response_id=state.get("menu_image_response_id", "")).bind_tools([tool])
    else:
        model = ChatOpenAI(model="gpt-5", output_version="responses/v1").bind_tools([tool])

    
    system_prompt = f"""You are an expert menu designer and culinary consultant with extensive experience in creating comprehensive, well-structured restaurant menus. Your specialty is translating restaurant concepts into compelling menu layouts that drive sales and enhance the dining experience.

RESTAURANT INFORMATION:
- Restaurant Name: {state.get("restaurant_name", "")}
- Cuisine Type: {state.get("cuisine_type", "")}
- Location: {state.get("location", "")}
- Target Audience: {state.get("target_audience", "")}
- Budget Range: {state.get("budget_range", "")}

MENU DESIGN OBJECTIVES:
1. Create a comprehensive menu structure with logical categorization
2. Establish strategic pricing that aligns with the budget range and target market
3. Ensure menu items authentically represent the cuisine type and appeal to the target audience
4. Consider local market preferences and dietary trends for the specified location
5. USE LARGER FONTS TO MAKE THE MENU FEEL FULL

MENU STRUCTURE REQUIREMENTS:
- Organize items into clear sections (appetizers, mains, desserts)
- Include dietary indicators (vegetarian, vegan, gluten-free, etc.) where relevant

EDITING CAPABILITIES:
You can help make specific modifications to any part of the menu:
- Add, remove, or modify individual menu items
- Adjust descriptions to emphasize different aspects (ingredients, preparation, origin)
- Revise pricing strategies for specific items or entire sections
- Reorganize menu sections or categories
- Update items to reflect seasonal availability or dietary preferences
- Customize descriptions for different target audiences

FORMAT INSTRUCTIONS:
Present the menu in a clear, restaurant-ready format with:
- Section headers clearly marked
- Item names that are memorable and appealing
- Pricing displayed consistently
- Descriptions that are informative yet concise
- Visual hierarchy that guides the customer's eye

Here's the previous menu text for context (if applicable):

<previous_menu_text>
{state.get("menu_text", "")}
</previous_menu_text>

Generate a complete menu that authentically represents this restaurant concept and appeals to the identified target market.

BEFORE RESPONDING ALWAYS USE YOUR IMAGE GENERATION TOOL TO GENERATE A VISUAL MENU!"""
    
    # get last human message
    last_human_message = state.get("messages", [])[-1]

    # Build messages with image if available
    messages = [SystemMessage(content=system_prompt), last_human_message]
    
    response = await model.ainvoke(messages)
    
    menu_text = ""
    if hasattr(response, 'content') and isinstance(response.content, list):
        for content_item in response.content:
            # Text content (menu)
            if content_item.get('type') == 'text':
                menu_text = content_item.get('text', '')

    
    return {
        "messages": response,
        "menu_image_response_id": response.id,
        "menu_text": menu_text
    }


# conditional edge to determine whether to parse the report or generate the menu
async def parse_report_or_generate_menu(state: VisualBrandingState):
    """Parse the report and generate the menu"""
    if state.get("restaurant_name", "") != "" or state.get("final_report") == "":
        return "menu"
    else:
        return "report"


# Build the visual branding subgraph
graph = StateGraph(state_schema=VisualBrandingState, input_schema=Input)

# Add nodes
graph.add_node("parse_report", parse_report)
graph.add_node("menu_agent", menu_agent)

graph.add_conditional_edges(
    START,
    # Function representing our conditional edge
    parse_report_or_generate_menu,
    {
        # If we want to generate the menu, we go to the generate_menu node.
        "menu": "menu_agent",
        # Otherwise we parse the report.
        "report": "parse_report",
    },
)
graph.add_edge("parse_report", "menu_agent")
graph.add_edge("menu_agent", END)


# Compile the subgraph
compiled_graph = graph.compile()