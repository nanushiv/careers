"use client";

import { useEffect } from "react";

export default function TawkChat() {
  const propertyId = process.env.NEXT_PUBLIC_TAWK_PROPERTY_ID;
  const widgetId = process.env.NEXT_PUBLIC_TAWK_WIDGET_ID || "default";

  useEffect(() => {
    if (!propertyId) return;

    const s = document.createElement("script");
    s.async = true;
    s.src = `https://embed.tawk.to/${propertyId}/${widgetId}`;
    s.charset = "UTF-8";
    s.setAttribute("crossorigin", "*");
    document.head.appendChild(s);

    return () => {
      // Clean up on unmount (SPA navigation)
      document.head.removeChild(s);
    };
  }, [propertyId, widgetId]);

  return null;
}
