"""Visual branding subgraph with branding, storefront, and menu generation nodes."""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph, MessagesState



class Input(MessagesState):
    """Input for visual menu generation."""
    final_report: Optional[str] = Field(default="", description="The final report from the deep researcher")



class VisualBrandingState(MessagesState):
    """State for visual branding generation workflow."""
    # Input from restaurant research
    final_report: Optional[str] = Field(default="", description="The final report from the deep researcher")
    restaurant_name: str = Field(default="", description="The name of the restaurant")
    cuisine_type: str = Field(default="", description="The type of cuisine the restaurant serves")
    location: str = Field(default="", description="The location of the restaurant")
    target_audience: str = Field(default="", description="The target audience for the restaurant")
    budget_range: str = Field(default="", description="The budget range for the restaurant")

    # Generated branding assets
    brand_concept: str = Field(default="", description="The brand concept for the restaurant")
    logo_image: str = Field(default="", description="The image of the logo")
    # storefront_image: str = Field(default="", description="The image of the storefront")
    menu_image: str = Field(default="", description="The image of the menu")


async def parse_report(state: VisualBrandingState):
    """Parse the report and update the state"""
    class Report(BaseModel):
        restaurant_name: str
        cuisine_type: str
        location: str
        target_audience: str
        budget_range: str

    model = ChatOpenAI(model="gpt-5")
    
    system_prompt = f"""Please parse this reports and return the restaurant name, 
cuisine type, location, target audience and budget range.

Report: {state.get("final_report", "")}

Return the restaurant name, cuisine type, location, target audience and budget range.
"""

    response = await model.with_structured_output(Report).ainvoke([
        SystemMessage(content=system_prompt)
    ])

    return {
        "restaurant_name": response.restaurant_name,
        "cuisine_type": response.cuisine_type,
        "location": response.location,
        "target_audience": response.target_audience,
        "budget_range": response.budget_range
    }


async def generate_menu(state: VisualBrandingState):
    """Generate restaurant brand concept and logo."""
    
    tool = { "type": "image_generation" }
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
2. Develop appetizing dish descriptions that highlight key ingredients and cooking methods
3. Establish strategic pricing that aligns with the budget range and target market
4. Ensure menu items authentically represent the cuisine type and appeal to the target audience
5. Consider local market preferences and dietary trends for the specified location

MENU STRUCTURE REQUIREMENTS:
- Organize items into clear sections (appetizers, mains, desserts)
- Include 4-6 signature dishes that define the restaurant's identity
- Provide detailed descriptions (1-2sentences) that create desire and set expectations
- Price items strategically within the specified budget range
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

Here's the conversation history as well for context:

<conversation history>
{state.get("messages", [])}
</conversation history>

Generate a complete menu that authentically represents this restaurant concept and appeals to the identified target market."""
    
    
    response = await model.ainvoke([
        SystemMessage(content=system_prompt)
    ])
    
    return {
        "messages": [response]
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
graph.add_node("generate_menu", generate_menu)

graph.add_conditional_edges(
    START,
    # Function representing our conditional edge
    parse_report_or_generate_menu,
    {
        # If we want to generate the menu, we go to the generate_menu node.
        "menu": "generate_menu",
        # Otherwise we parse the report.
        "report": "parse_report",
    },
)
graph.add_edge("parse_report", "generate_menu")
graph.add_edge("generate_menu", "end")


# Compile the subgraph
compiled_graph = graph.compile()