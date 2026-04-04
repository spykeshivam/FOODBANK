from flask import Blueprint, redirect, send_file, jsonify
from services import data_service, graph_service

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route("/dashboard")
def dashboard():
    """
    Redirects to the Dash dashboard.
    """
    return redirect("/dashboard/")


@dashboard_bp.route("/download_dashboard", methods=["GET"])
def download_dashboard():
    """
    Generates a PDF of the dashboard and triggers a download.
    """
    try:
        users_df, logins_df = data_service.get_all_data_frames()
        pdf_buffer = graph_service.create_dashboard_pdf(users_df, logins_df)
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name="dashboard_plots.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
