from flask import Flask, jsonify, request

from router import ModelRouter
from director import AIDirector
from llm_router import LLMRouter
from llm_provider import LLMProviderError
from storage import Storage
from jobs import JobManager
from video_provider import VideoRouter, VideoProviderError
from audio_provider import AudioRouter


app = Flask(__name__)

router = ModelRouter()
director = AIDirector()
llm_router = LLMRouter()
storage = Storage()
video_router = VideoRouter()
audio_router = AudioRouter()
jobs = JobManager(
    storage,
    llm_router,
    video_router,
    audio_router,
)


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "service": "MJK Video AI Backend",
        "version": "0.4.0",
        "router": True,
        "storage": True,
        "jobs": True,
        "video_router": True,
        "audio_router": True,
    })


@app.get("/v1/models")
def models():
    return jsonify({
        "ok": True,
        "models": router.available_models()
    })


@app.get("/v1/video/status")
def video_status():
    return jsonify({
        "ok": True,
        "status": video_router.status(),
    })


@app.get("/v1/audio/status")
def audio_status():
    return jsonify({
        "ok": True,
        "status": audio_router.status(),
    })


@app.post("/v1/director/create")
def create_director_plan():
    data = request.get_json(silent=True) or {}

    try:
        plan = director.create(data)
        return jsonify({"ok": True, "plan": plan})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": "internal_error",
            "details": str(exc),
        }), 500


@app.post("/v1/projects/plan")
def create_plan():
    data = request.get_json(silent=True) or {}

    try:
        plan = router.create_plan(data)
        return jsonify({"ok": True, "plan": plan})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": "internal_error",
            "details": str(exc),
        }), 500


@app.post("/v1/projects/jobs")
def create_project_job():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()

    if len(prompt) < 3:
        return jsonify({
            "ok": False,
            "error": "prompt is required",
        }), 400

    try:
        project = storage.create_project({
            "prompt": prompt,
            "duration_seconds": int(
                data.get("duration_seconds", 30)
            ),
            "style": str(
                data.get("style", "cinematic")
            ),
            "language": str(
                data.get("language", "فارسی")
            ),
            "aspect_ratio": str(
                data.get("aspect_ratio", "16:9")
            ),
            "output_type": str(
                data.get("output_type", "general")
            ),
        })

        project = jobs.submit_director_job(project)

        return jsonify({
            "ok": True,
            "project": project,
        }), 202

    except ValueError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 400
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": "internal_error",
            "details": str(exc),
        }), 500


@app.post("/v1/projects/<project_id>/generate-video")
def generate_project_video(project_id):
    data = request.get_json(silent=True) or {}

    try:
        project = storage.get_project(project_id)
    except KeyError:
        return jsonify({
            "ok": False,
            "error": "project_not_found",
        }), 404

    if not project.get("plan"):
        return jsonify({
            "ok": False,
            "error": "director_plan_not_ready",
        }), 409

    try:
        project = jobs.submit_video_job(
            project_id,
            preferred_provider=data.get("provider"),
        )

        return jsonify({
            "ok": True,
            "project": project,
        }), 202

    except VideoProviderError as exc:
        return jsonify({
            "ok": False,
            "error": "video_provider_error",
            "details": str(exc),
        }), 503
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": "internal_error",
            "details": str(exc),
        }), 500


@app.get("/v1/projects/<project_id>")
def get_project(project_id):
    try:
        return jsonify({
            "ok": True,
            "project": storage.get_project(project_id),
        })
    except KeyError:
        return jsonify({
            "ok": False,
            "error": "project_not_found",
        }), 404


@app.get("/v1/projects/<project_id>/files")
def get_project_files(project_id):
    try:
        storage.get_project(project_id)
        return jsonify({
            "ok": True,
            "files": storage.list_files(project_id),
        })
    except KeyError:
        return jsonify({
            "ok": False,
            "error": "project_not_found",
        }), 404


@app.get("/v1/llm/status")
def llm_status():
    return jsonify({
        "ok": True,
        "status": llm_router.status(),
    })


@app.post("/v1/llm/director-request")
def llm_director_request():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()

    if len(prompt) < 3:
        return jsonify({
            "ok": False,
            "error": "prompt is required",
        }), 400

    try:
        plan = llm_router.build_director_request(
            prompt=prompt,
            duration_seconds=int(
                data.get("duration_seconds", 30)
            ),
            style=str(
                data.get("style", "cinematic")
            ),
            language=str(
                data.get("language", "فارسی")
            ),
            aspect_ratio=str(
                data.get("aspect_ratio", "16:9")
            ),
            output_type=str(
                data.get("output_type", "general")
            ),
        )

        return jsonify({
            "ok": True,
            "request": plan,
        })
    except ValueError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 400
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": "internal_error",
            "details": str(exc),
        }), 500


@app.post("/v1/llm/director-generate")
def llm_director_generate():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()

    if len(prompt) < 3:
        return jsonify({
            "ok": False,
            "error": "prompt is required",
        }), 400

    try:
        plan = llm_router.generate_director_plan(
            prompt=prompt,
            duration_seconds=int(
                data.get("duration_seconds", 30)
            ),
            style=str(
                data.get("style", "cinematic")
            ),
            language=str(
                data.get("language", "فارسی")
            ),
            aspect_ratio=str(
                data.get("aspect_ratio", "16:9")
            ),
            output_type=str(
                data.get("output_type", "general")
            ),
        )

        return jsonify({
            "ok": True,
            "plan": plan,
        })
    except LLMProviderError as exc:
        return jsonify({
            "ok": False,
            "error": "llm_provider_error",
            "details": str(exc),
        }), 502
    except ValueError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
        }), 400
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": "internal_error",
            "details": str(exc),
        }), 500


if __name__ == "__main__":
    import os

    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
