import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './App.css'
import './mascots-preview.css'
import { Characters } from './App.jsx'

// App.jsx 의 <svg viewBox> 와 같아야 한다. 바꾸면 여기도 같이 바꾼다.
const VIEW = { x: 5, w: 250, h: 141 }

// 캐릭터 한 마리만 잘라서 크게 본다.
// viewBox 는 그대로 두고 크게 그린 뒤 창으로 가린다. 실제 화면과 같은 도형을 보게 된다.
// 창 아래 빨간 선이 표지의 흰색/노란색 경계선 자리다. 발끝이 여기 닿아야 한다.
function Crop({ label, from, to, top = 0, scale }) {
  return (
    <figure className="crop">
      <figcaption>
        {label} <span className="crop-note">{scale}배</span>
      </figcaption>
      <div
        className="crop-window"
        style={{ width: (to - from) * scale, height: (VIEW.h - top) * scale }}
      >
        <div
          className="crop-slide"
          style={{
            width: VIEW.w * scale,
            marginLeft: -(from - VIEW.x) * scale,
            marginTop: -top * scale,
          }}
        >
          <Characters />
        </div>
      </div>
    </figure>
  )
}

function Preview() {
  return (
    <div className="preview">
      <div className="crop-row">
        <Crop label="토끼" from={36} to={120} top={4} scale={3} />
        <Crop label="강아지" from={134} to={226} top={40} scale={3} />
      </div>

      {/* 실제 표지 배치. 경계선 위에 제대로 서 있는지 눈으로 한 번 더 본다 */}
      <figure>
        <figcaption>
          표지 배치 <span className="crop-note">흰색/노란색 경계선</span>
        </figcaption>
        <div className="hero stage">
          <div className="hero-sky">
            <Characters />
          </div>
          <div />
        </div>
      </figure>
    </div>
  )
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Preview />
  </StrictMode>,
)
