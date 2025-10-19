import streamlit as st
import base64


def img_to_data_url(file) -> str:
    if file is None:
        return ""
    bytes_data = file.read()
    mime = getattr(file, "type", "image/png")
    b64 = base64.b64encode(bytes_data).decode()
    return f"data:{mime};base64,{b64}"


st.set_page_config(page_title="eSignature Composer", layout="wide")
st.title("eSignature Composer")


def main():
    col1, col2 = st.columns([1, 3])

    with col1:
        bg_file = st.file_uploader("Upload background image", type=["png", "jpg", "jpeg"], key="bg")
        sig_file = st.file_uploader("Upload signature image (PNG recommended)", type=["png", "jpg", "jpeg"], key="sig")

        min_thresh = st.slider("Alpha min threshold (keep if between min and max)", 0, 255, 0)
        max_thresh = st.slider("Alpha max threshold (keep if between min and max)", 0, 255, 255)

        reset = st.button("Reset size/position")

        st.markdown("---")
        st.write(
            "Note: Use the anchors to resize the signature. Drag to move. Use Download button inside the canvas to save the composited image."
        )

    with col2:
        bg_data = img_to_data_url(bg_file) if bg_file else ""
        sig_data = img_to_data_url(sig_file) if sig_file else ""

        if not bg_data and not sig_data:
            st.info("Upload a background image and a signature image to get started.")
            return

        html_template = '''
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>eSignature Canvas</title>
    <script src="https://unpkg.com/konva@8/konva.min.js"></script>
    <style>
      html, body, #container { height: 100%; margin: 0; padding: 0; overflow: hidden; }
      #stage-parent { width: 100%; height: 100%; position: relative; background: #222; display:flex; align-items:center; justify-content:center; }
      #top-controls { position: absolute; top: 8px; left: 8px; z-index: 10; background: rgba(255,255,255,0.9); padding: 6px; border-radius: 6px; }
      button { margin: 2px; }
    </style>
  </head>
  <body>
      <div id="stage-parent">
      <div id="top-controls">
        <button id="resetBtn">Reset</button>
        <button id="downloadBtn">Download</button>
      </div>
      <div id="stage-container" style="width:100%; height:100%; overflow:hidden;"></div>
    </div>

    <script>
  const bgSrc = "{BG}";
  const sigSrc = "{SIG}";
  let alphaMin = {MIN};
  let alphaMax = {MAX};
  const resetFlag = {RESET};

      function fitImageToStage(imgObj, stageWidth, stageHeight) {
        const imgW = imgObj.width;
        const imgH = imgObj.height;
        // use contain (fit) so the background fully fits inside the stage without overflowing
        const scale = Math.min(stageWidth / imgW, stageHeight / imgH);
        return { width: imgW * scale, height: imgH * scale, scale };
      }

      function applyAlphaThresholdToDataURL(img, minThreshold, maxThreshold, callback) {
        if (!img) { callback(null); return; }
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        try {
          const imageData = ctx.getImageData(0,0,canvas.width,canvas.height);
          const data = imageData.data;
          // color-based/alpha-based masking: remove pixels that are outside the alpha range
          // or are near-white (common scanned signature background)
          const whiteThresh = 240; // any RGB above this is considered white
          for (let i = 0; i < data.length; i += 4) {
            const r = data[i];
            const g = data[i+1];
            const b = data[i+2];
            const a = data[i+3];
            // treat near-white pixels as background regardless of alpha
            const isNearWhite = (r >= whiteThresh && g >= whiteThresh && b >= whiteThresh);
            if (isNearWhite || a < minThreshold || a > maxThreshold) {
              data[i+3] = 0;
            }
          }
          ctx.putImageData(imageData, 0, 0);
          callback(canvas.toDataURL());
        } catch (e) {
          console.warn('Image processing failed, falling back to global opacity', e);
          callback(null);
        }
      }

      function makeStage() {
        const parent = document.getElementById('stage-container');
        const width = parent.clientWidth || window.innerWidth;
        const height = parent.clientHeight || window.innerHeight;
        parent.innerHTML = '';

        const stage = new Konva.Stage({
          container: parent,
          width: width,
          height: height,
        });

        const layer = new Konva.Layer();
        stage.add(layer);

        const bg = new Image();
        bg.crossOrigin = 'Anonymous';
        bg.src = bgSrc || '';
        const bgKonva = new Konva.Image();
        layer.add(bgKonva);

        let bgReady = false;
        bg.onload = () => {
          const fitted = fitImageToStage(bg, stage.width(), stage.height());
          bgKonva.image(bg);
          bgKonva.x((stage.width() - fitted.width) / 2);
          bgKonva.y((stage.height() - fitted.height) / 2);
          bgKonva.width(fitted.width);
          bgKonva.height(fitted.height);
          layer.batchDraw();
          bgReady = true;
          tryInitSignature();
        };

  const sigImg = new Image();
  sigImg.crossOrigin = 'Anonymous';
  sigImg.src = sigSrc || '';
  let sigReady = false;

        const sigKonva = new Konva.Image({
          x: stage.width() / 2 - 100,
          y: stage.height() / 2 - 50,
          draggable: true,
        });
        layer.add(sigKonva);

        // constrain dragging to background bounds (will update bounds when bg is ready)
        sigKonva.dragBoundFunc(function(pos) {
          if (!bgKonva.image()) return pos;
          const scaleX = sigKonva.scaleX() || 1;
          const scaleY = sigKonva.scaleY() || 1;
          const sigW = sigKonva.width() * scaleX;
          const sigH = sigKonva.height() * scaleY;
          const minX = bgKonva.x();
          const minY = bgKonva.y();
          const maxX = bgKonva.x() + bgKonva.width() - sigW;
          const maxY = bgKonva.y() + bgKonva.height() - sigH;
          const nx = Math.max(minX, Math.min(pos.x, maxX));
          const ny = Math.max(minY, Math.min(pos.y, maxY));
          return { x: nx, y: ny };
        });

        const transformer = new Konva.Transformer({
          nodes: [sigKonva],
          enabledAnchors: [
            'top-left','top-center','top-right',
            'middle-left','middle-right',
            'bottom-left','bottom-center','bottom-right'
          ],
          rotateEnabled: false,
          boundBoxFunc: function(oldBox, newBox) {
            // keep the transformed box within background bounds
            if (!bgKonva.image()) return oldBox;
            const minX = bgKonva.x();
            const minY = bgKonva.y();
            const maxX = bgKonva.x() + bgKonva.width();
            const maxY = bgKonva.y() + bgKonva.height();
            const nx = Math.max(minX, Math.min(newBox.x, maxX - newBox.width));
            const ny = Math.max(minY, Math.min(newBox.y, maxY - newBox.height));
            return { x: nx, y: ny, width: Math.min(newBox.width, maxX - nx), height: Math.min(newBox.height, maxY - ny) };
          }
        });
        layer.add(transformer);

        let initialState = null;

        function setInitialState() {
          initialState = { x: sigKonva.x(), y: sigKonva.y(), width: sigKonva.width(), height: sigKonva.height(), scaleX: sigKonva.scaleX(), scaleY: sigKonva.scaleY() };
          // If Streamlit reset was clicked, force the signature back to initial state
          if (resetFlag) {
            sigKonva.x(initialState.x);
            sigKonva.y(initialState.y);
            sigKonva.scaleX(1);
            sigKonva.scaleY(1);
            sigKonva.width(initialState.width);
            sigKonva.height(initialState.height);
            layer.batchDraw();
          }
        }

        // Minimum displayed size for the signature (in pixels)
        const MIN_WIDTH = 20;
        const MIN_HEIGHT = 10;

        // Save transform (stores displayed width/height so restores are stable)
        function saveTransform() {
          const dispW = sigKonva.width() * (sigKonva.scaleX() || 1);
          const dispH = sigKonva.height() * (sigKonva.scaleY() || 1);
          const data = { x: sigKonva.x(), y: sigKonva.y(), width: dispW, height: dispH };
          localStorage.setItem('esignature_transform', JSON.stringify(data));
        }

        // Enforce minimum size while transforming
        sigKonva.on('transform', function() {
          const minScaleX = MIN_WIDTH / (sigKonva.width() || 1);
          const minScaleY = MIN_HEIGHT / (sigKonva.height() || 1);
          if ((sigKonva.scaleX() || 1) < minScaleX) sigKonva.scaleX(minScaleX);
          if ((sigKonva.scaleY() || 1) < minScaleY) sigKonva.scaleY(minScaleY);
        });

        // Save on drag end
        sigKonva.on('dragend', saveTransform);

        // On transform end, normalize scale into width/height and clamp position within background
        sigKonva.on('transformend', function() {
          const newW = Math.max(sigKonva.width() * (sigKonva.scaleX() || 1), MIN_WIDTH);
          const newH = Math.max(sigKonva.height() * (sigKonva.scaleY() || 1), MIN_HEIGHT);
          let nx = sigKonva.x();
          let ny = sigKonva.y();
          const bgX = bgKonva.x();
          const bgY = bgKonva.y();
          const bgW = bgKonva.width();
          const bgH = bgKonva.height();
          if (nx < bgX) nx = bgX;
          if (ny < bgY) ny = bgY;
          if (nx + newW > bgX + bgW) nx = bgX + bgW - newW;
          if (ny + newH > bgY + bgH) ny = bgY + bgH - newH;
          sigKonva.scaleX(1);
          sigKonva.scaleY(1);
          sigKonva.width(newW);
          sigKonva.height(newH);
          sigKonva.x(nx);
          sigKonva.y(ny);
          layer.batchDraw();
          saveTransform();
        });

        function tryInitSignature() {
          if (!bgReady || !sigReady) return;
          // Use background displayed dimensions to size/position signature
          const bgDisplayed = bgKonva;
          applyAlphaThresholdToDataURL(sigImg, alphaMin, alphaMax, (processedDataUrl) => {
            if (processedDataUrl) {
              const finalImg = new Image();
              finalImg.crossOrigin = 'Anonymous';
              finalImg.src = processedDataUrl;
              finalImg.onload = () => {
                sigKonva.image(finalImg);
                // bind signature size to background displayed width (20% by default)
                const targetW = (bgDisplayed.width() || stage.width()) * 0.2;
                const scale = targetW / finalImg.width;
                sigKonva.width(finalImg.width);
                sigKonva.height(finalImg.height);
                sigKonva.scale({ x: scale, y: scale });
                // center signature over the background image unless a saved transform exists
                const saved = localStorage.getItem('esignature_transform');
                if (saved) {
                  try {
                    const obj = JSON.parse(saved);
                    sigKonva.x(obj.x);
                    sigKonva.y(obj.y);
                    sigKonva.scaleX(obj.scaleX || scale);
                    sigKonva.scaleY(obj.scaleY || scale);
                    sigKonva.width(obj.width || finalImg.width);
                    sigKonva.height(obj.height || finalImg.height);
                  } catch (e) {
                    // fallback to centered
                    const sigW = finalImg.width * scale;
                    const sigH = finalImg.height * scale;
                    sigKonva.x(bgDisplayed.x() + (bgDisplayed.width() - sigW) / 2);
                    sigKonva.y(bgDisplayed.y() + (bgDisplayed.height() - sigH) / 2);
                  }
                } else {
                  const sigW = finalImg.width * scale;
                  const sigH = finalImg.height * scale;
                  sigKonva.x(bgDisplayed.x() + (bgDisplayed.width() - sigW) / 2);
                  sigKonva.y(bgDisplayed.y() + (bgDisplayed.height() - sigH) / 2);
                }
                transformer.nodes([sigKonva]);
                layer.batchDraw();
                setInitialState();
                // save transform on interactions
                function saveTransform() {
                  const data = {
                    x: sigKonva.x(),
                    y: sigKonva.y(),
                    scaleX: sigKonva.scaleX(),
                    scaleY: sigKonva.scaleY(),
                    width: sigKonva.width(),
                    height: sigKonva.height()
                  };
                  localStorage.setItem('esignature_transform', JSON.stringify(data));
                }
                sigKonva.on('dragend', saveTransform);
                sigKonva.on('transformend', saveTransform);
              };
            } else {
              // fallback: use original image and apply a global opacity based on the min/max
              sigKonva.image(sigImg);
              const targetW = (bgDisplayed.width() || stage.width()) * 0.2;
              const scale = targetW / sigImg.width;
              sigKonva.width(sigImg.width);
              sigKonva.height(sigImg.height);
              sigKonva.scale({ x: scale, y: scale });
              const sigW = sigImg.width * scale;
              const sigH = sigImg.height * scale;
              sigKonva.x(bgDisplayed.x() + (bgDisplayed.width() - sigW) / 2);
              sigKonva.y(bgDisplayed.y() + (bgDisplayed.height() - sigH) / 2);
              // approximate opacity: based on min threshold
              const opacity = 1 - (alphaMin / 255);
              sigKonva.opacity(opacity);
              transformer.nodes([sigKonva]);
              layer.batchDraw();
              setInitialState();
            }
          });
        }

        sigImg.onload = () => { sigReady = true; tryInitSignature(); };

        window.addEventListener('resize', () => {
          const pw = parent.clientWidth || window.innerWidth;
          const ph = parent.clientHeight || window.innerHeight;
          stage.width(pw);
          stage.height(ph);
          if (bgKonva.image()) {
            const bimg = bgKonva.image();
            const fitted = fitImageToStage(bimg, stage.width(), stage.height());
            bgKonva.x((stage.width() - fitted.width) / 2);
            bgKonva.y((stage.height() - fitted.height) / 2);
            bgKonva.width(fitted.width);
            bgKonva.height(fitted.height);
          }
          layer.batchDraw();
        });

        // thresholds come from Streamlit UI (min/max). To change them, update sliders in the Streamlit app and the component will re-render.

        document.getElementById('resetBtn').addEventListener('click', () => {
          if (initialState) {
            sigKonva.x(initialState.x);
            sigKonva.y(initialState.y);
            sigKonva.scaleX(1);
            sigKonva.scaleY(1);
            sigKonva.width(initialState.width);
            sigKonva.height(initialState.height);
            layer.batchDraw();
          }
        });

        document.getElementById('downloadBtn').addEventListener('click', () => {
          const vis = transformer.visible();
          transformer.hide();
          layer.batchDraw();
          const dataURL = stage.toDataURL({ pixelRatio: 1 });
          if (vis) { transformer.show(); layer.batchDraw(); }
          const link = document.createElement('a');
          link.href = dataURL;
          link.download = 'signed-image.png';
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        });

        return { stage, layer, bgKonva, sigKonva, transformer };
      }

      const created = makeStage();
      window.setTimeout(() => created.layer.draw(), 50);
    </script>
  </body>
</html>
'''

        reset_flag = 'true' if reset else 'false'
        html = html_template.replace('{BG}', bg_data).replace('{SIG}', sig_data).replace('{MIN}', str(min_thresh)).replace('{MAX}', str(max_thresh)).replace('{RESET}', reset_flag)

        # Shrink component height so it fits alongside left controls
        st.components.v1.html(html, height=520, scrolling=False)


if __name__ == '__main__':
    main()
