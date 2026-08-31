export default function ThemeToast({ message }) {
  if (!message) return null;

  return (
    <div className="theme-toast" role="status" aria-live="polite">
      {message}
    </div>
  );
}
