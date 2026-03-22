from flask import Blueprint, render_template, request, send_file, redirect
from services import data_service, graph_service

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route("/dashboard")
def dashboard():
    """
    Redirects to the Dash dashboard.
    """
    return redirect("/dashboard/")

@dashboard_bp.route("/statistics", methods=["GET", "POST"])
def statistics():
    """
    Handles the 'Descriptive Statistics' page for specific date queries.
    """
    result = None
    input_date = None

    if request.method == "POST":
        input_date = request.form.get("date")
        # Delegate the date parsing and counting to the service
        #
        result = data_service.get_login_count_for_date(input_date)

    return render_template("statistics.html", result=result, date=input_date)

@dashboard_bp.route("/download_dashboard", methods=["GET"])
def download_dashboard():
    """
    Generates a PDF of the dashboard and triggers a download.
    """
    users_df, logins_df = data_service.get_all_data_frames()
    
    # The service returns a BytesIO buffer
    #
    pdf_buffer = graph_service.create_dashboard_pdf(users_df, logins_df)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="dashboard_plots.pdf",
        mimetype="application/pdf"
    )
