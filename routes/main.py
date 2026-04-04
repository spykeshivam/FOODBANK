from flask import Blueprint, render_template, request
from services import data_service

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def home():
    return render_template("home.html")

@main_bp.route("/search")
def search():
    return render_template("search.html")

@main_bp.route("/search_user", methods=["POST"])
def search_user():
    search_type = request.form.get("search_type")
    query_name = request.form.get("name", "").strip()
    query_postcode = request.form.get("postcode", "").strip()
    query_dob = request.form.get("dob", "").strip()

    results, message = data_service.perform_search(
        search_type, 
        name=query_name, 
        postcode=query_postcode, 
        dob=query_dob
    )

    return render_template("search.html", results=results, message=message)