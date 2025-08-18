# Menu Generation Agent (Simple Version)

A LangGraph-powered agent that generates restaurant menu concepts from PDF reports and creates visual menu designs with iterative user feedback. This version is much simpler than the main agent created for a demo.

## Overview

This agent takes restaurant concept reports (converted from PDF to markdown) and generates:
2. **Visual Menu Design** - Generated menu images with proper styling
3. **Iterative Refinement** - User feedback loop for visuals

## Setup

This project uses **uv** as the package manager for dependency management.

### Prerequisites
- Python 3.8+
- uv package manager
- LangGraph CLI

### Installation

1. Install dependencies:
```bash
uv sync
```

2. Start the local LangGraph server:
```bash
langgraph dev
```

## Usage


### Agent Workflow

1. **Report Parsing** - Extracts restaurant name, cuisine, location, and budget range
2. **Visual Menu Generation** - Creates styled menu images using image generation tools

## Project Structure

- `agent.py` - Main LangGraph agent implementation
- `langgraph.json` - LangGraph server configuration

## Features


- **Feedback Loops** - Iterative improvement based on user input  
- **State Management** - Robust state tracking through the workflow

## Development

Start the development server:
```bash
langgraph dev
```

The agent will be available for testing through the LangGraph interface.