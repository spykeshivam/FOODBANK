from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from services import data_service

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login")
def index():
    """Renders the login page."""
    #
    return render_template("index.html")

@auth_bp.route("/check_user", methods=["POST"])
def check_user():
    """
    Checks if a user ID exists in the system.
    """
    user_id = request.form.get("user_id", "").strip()
    
    if not user_id:
        return jsonify({"message": "Login Error: No ID provided", "exists": False})

    try:
        # Service returns a dictionary with 'exists', 'message', and 'details'
        #
        response_data = data_service.get_user_details(user_id)
        return jsonify(response_data)
    except Exception as exc:
        return (
            jsonify({"message": f"Server Error: {str(exc)}", "exists": False}),
            500,
        )

@auth_bp.route("/log_login", methods=["POST"])
def log_login():
    """
    Logs the user login.
    Includes duplicate check (debouncing) in the service layer.
    """
    user_id = request.form.get("user_id", "").strip()
    
    if user_id:
        # The service layer will now handle the timestamp check
        # to prevent duplicate entries within 5 minutes.
        #
        try:
            success, message = data_service.append_login(user_id)
            return jsonify({"message": message, "success": success})
        except Exception as exc:
            return (
                jsonify({"message": f"Server Error: {str(exc)}", "success": False}),
                500,
            )
    
    return jsonify({"message": "Login Error: No ID provided", "success": False})


@auth_bp.route("/update_postcode", methods=["GET", "POST"])
def update_postcode():
    """
    GET  — show the postcode correction form (user_id passed as query param).
    POST — validate and save the new postcode, then redirect back to login.
    """
    if request.method == "GET":
        user_id = request.args.get("user_id", "").strip()
        return render_template("update_postcode.html", user_id=user_id, error=None)

    user_id = request.form.get("user_id", "").strip()
    new_postcode = request.form.get("postcode", "").strip()

    success, message = data_service.update_postcode(user_id, new_postcode)

    if success:
        return redirect(url_for("auth.index"))

    return render_template("update_postcode.html", user_id=user_id, error=message)
