import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

function placePopup(button) {
  const rect = button.getBoundingClientRect();
  const gap = 8;
  const maxWidth = 240;
  const margin = 12;
  const centerX = rect.left + rect.width / 2;
  const minLeft = margin + maxWidth / 2;
  const maxLeft = window.innerWidth - margin - maxWidth / 2;
  const left = Math.min(maxLeft, Math.max(minLeft, centerX));

  const spaceBelow = window.innerHeight - rect.bottom - gap;
  const spaceAbove = rect.top - gap;
  const showBelow = spaceBelow >= 72 || spaceBelow >= spaceAbove;

  if (showBelow) {
    return {
      top: rect.bottom + gap,
      left,
      placement: "bottom",
    };
  }

  return {
    top: rect.top - gap,
    left,
    placement: "top",
  };
}

export default function InfoTip({ label, tip }) {
  const tipId = useId();
  const btnRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [style, setStyle] = useState(null);

  function show() {
    const button = btnRef.current;
    if (!button) return;
    const next = placePopup(button);
    setStyle(next);
    setOpen(true);
  }

  function hide() {
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return undefined;

    function refresh() {
      const button = btnRef.current;
      if (!button) return;
      setStyle(placePopup(button));
    }

    window.addEventListener("scroll", hide, true);
    window.addEventListener("resize", refresh);
    return () => {
      window.removeEventListener("scroll", hide, true);
      window.removeEventListener("resize", refresh);
    };
  }, [open]);

  const popup =
    open && style
      ? createPortal(
          <span
            id={tipId}
            role="tooltip"
            className={`info-tip-popup info-tip-popup--fixed info-tip-popup--${style.placement}`}
            style={{
              top: style.top,
              left: style.left,
              transform:
                style.placement === "top"
                  ? "translate(-50%, -100%)"
                  : "translateX(-50%)",
            }}
          >
            {tip}
          </span>,
          document.body,
        )
      : null;

  return (
    <>
      <span className="info-tip">
        {label}
        <button
          ref={btnRef}
          type="button"
          className="info-tip-btn"
          aria-label={`Información sobre ${label}`}
          aria-describedby={open ? tipId : undefined}
          onMouseEnter={show}
          onMouseLeave={hide}
          onFocus={show}
          onBlur={hide}
        >
          ⓘ
        </button>
      </span>
      {popup}
    </>
  );
}
