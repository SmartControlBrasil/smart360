import os
import rcssmin
import rjsmin

STATIC_DIR = "static/institutional/eitech"

CSS_PLUGINS = [
    "css/plugins/bootstrap.min.css",
    "css/plugins/aos.css",
    "css/plugins/fontawesome.css",
    "css/plugins/magnific-popup.css",
    "css/plugins/mobile.css",
    "css/plugins/owlcarousel.min.css",
    "css/plugins/sidebar.css",
    "css/plugins/slick-slider.css",
    "css/plugins/nice-select.css",
]

CSS_MAIN = [
    "css/main.css",
    "css/scb-header.css",
    "css/scb-float-widgets.css",
]

JS_PLUGINS = [
    "js/plugins/bootstrap.min.js",
    "js/plugins/fontawesome.js",
    "js/plugins/aos.js",
    "js/plugins/counter.js",
    "js/plugins/gsap.min.js",
    "js/plugins/ScrollTrigger.min.js",
    "js/plugins/Splitetext.js",
    "js/plugins/SmoothScroll.js",
    "js/plugins/sidebar.js",
    "js/plugins/magnific-popup.js",
    "js/plugins/mobilemenu.js",
    "js/plugins/owlcarousel.min.js",
    "js/plugins/nice-select.js",
    "js/plugins/waypoints.js",
    "js/plugins/slick-slider.js",
    "js/plugins/circle-progress.js",
]

JS_MAIN = [
    "js/main.js"
]

def bundle_and_minify(files, output_filename, minify_func):
    bundled = []
    for f in files:
        filepath = os.path.join(STATIC_DIR, f)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as file:
                bundled.append(file.read())
        else:
            print(f"WARNING: File not found {filepath}")
    
    raw_content = "\n".join(bundled)
    minified_content = minify_func(raw_content)
    
    out_path = os.path.join(STATIC_DIR, output_filename)
    with open(out_path, "w", encoding="utf-8") as file:
        file.write(minified_content)
    
    print(f"Created {out_path} ({len(minified_content)} bytes)")

if __name__ == "__main__":
    bundle_and_minify(CSS_PLUGINS, "css/plugins.bundle.min.css", rcssmin.cssmin)
    bundle_and_minify(CSS_MAIN, "css/main.bundle.min.css", rcssmin.cssmin)
    bundle_and_minify(JS_PLUGINS, "js/plugins.bundle.min.js", rjsmin.jsmin)
    bundle_and_minify(JS_MAIN, "js/main.min.js", rjsmin.jsmin)
