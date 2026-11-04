def test_root_redirects_to_swagger_docs(client):
    response = client.get("/")

    assert response.status_code == 302  # temporary, so browsers don't cache it forever
    assert response["Location"] == "/api/docs"


def test_swagger_docs_page_loads(client):
    response = client.get("/api/docs")

    assert response.status_code == 200
    assert b"swagger-ui" in response.content
