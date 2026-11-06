export const metadata = { title: "FibSweep AI" };
export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: "#0b0f17", color: "#e6e9ef", fontFamily: "system-ui, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
