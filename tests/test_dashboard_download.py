import io

from services import data_service, graph_service


def test_download_dashboard_uses_pdf_builder(client, monkeypatch):
    monkeypatch.setattr(data_service, "get_all_data_frames", lambda: ([], []))
    monkeypatch.setattr(graph_service, "create_dashboard_pdf", lambda _u, _l: io.BytesIO(b"%PDF-1.4"))

    response = client.get("/download_dashboard")

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
