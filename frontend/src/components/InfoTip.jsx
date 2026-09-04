import { useId } from "react";

export default function InfoTip({ label, tip }) {
  const tipId = useId();
  return (
    <span className="info-tip">
      {label}
      <button
        type="button"
        className="info-tip-btn"
        aria-label={`Información sobre ${label}`}
        aria-describedby={tipId}
      >
        ⓘ
      </button>
      <span id={tipId} role="tooltip" className="info-tip-popup">
        {tip}
      </span>
    </span>
  );
}
