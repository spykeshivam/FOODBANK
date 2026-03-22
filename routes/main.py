from flask import Blueprint, render_template, request
# We will create this service in the next step
from services import data_service 

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def home():
    """Renders the main home page."""
    #
    return render_template("home.html")

@main_bp.route("/search")
def search():
    """Renders the search page."""
    #
    return render_template("search.html")

@main_bp.route("/search_user", methods=["POST"])
def search_user():
    """
    Handles user search logic. 
    Logic moved to data_service to keep route clean.
    """
    search_type = request.form.get("search_type")
    # Using .get() for safety against missing keys
    query_name = request.form.get("name", "").strip()
    query_postcode = request.form.get("postcode", "").strip()
    query_dob = request.form.get("dob", "").strip()
    
    # Delegate the search logic to the service layer
    #
    results, message = data_service.perform_search(
        search_type, 
        name=query_name, 
        postcode=query_postcode, 
        dob=query_dob
    )

    return render_template("search.html", results=results, message=message)