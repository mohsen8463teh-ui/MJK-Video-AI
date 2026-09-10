from flask import Flask, jsonify, request

from router import ModelRouter
from director import AIDirector
from llm_router import LLMRouter


app = Flask(__name__)

router = ModelRouter()
director = AIDirector()
llm_router = LLMRouter()


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "service": "MJK Video AI Backend",
        "version": "0.2.0",
        "router": True
    })


@app.get("/v1/models")
def models():
    return jsonify({
        "ok": True,
        "models": router.available_models()
    })

    
@app.post("/v1/director/create")
def create_director_plan():
    data = request.get_json(silent=True) or {}

    try:
        plan = director.create(data)

        return jsonify({
            "ok": True,
            "plan": plan
        })

    except ValueError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 400

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": "internal_error",
            "details": str(exc)
        }), 500


@app.post("/v1/projects/plan")
def create_plan():
    data = request.get_json(silent=True) or {}

    try:
        plan = router.create_plan(data)

        return jsonify({
            "ok": True,
            "plan": plan
        })

    except ValueError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 400

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": "internal_error",
            "details": str(exc)
        }), 500


@app.get("/v1/llm/status")
def llm_status():
    return jsonify({
        "ok": True,
        "status": llm_router.status()
    })


@app.post("/v1/llm/director-request")
def llm_director_request():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()

    if len(prompt) < 3:
        return jsonify({
            "ok": False,
            "error": "prompt is required"
        }), 400

    try:
        plan = llm_router.build_director_request(
            prompt=prompt,
            duration_seconds=int(data.get("duration_seconds", 30)),
            style=str(data.get("style", "cinematic")),
            language=str(data.get("language", "فارسی")),
            aspect_ratio=str(data.get("aspect_ratio", "16:9")),
            output_type=str(data.get("output_type", "general"))
        )

        return jsonify({
            "ok": True,
            "request": plan
        })

    except ValueError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 400

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": "internal_error",
            "details": str(exc)
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8000,
        debug=False
    )
