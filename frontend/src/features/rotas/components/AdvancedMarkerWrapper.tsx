import { useEffect, useRef } from 'react';
import { useGoogleMap } from '@react-google-maps/api';

interface AdvancedMarkerWrapperProps {
  position: google.maps.LatLngLiteral;
  title?: string;
  onClick?: () => void;
  content?: React.ReactNode;
}

export function AdvancedMarkerWrapper({ position, title, onClick, content }: AdvancedMarkerWrapperProps) {
  const map = useGoogleMap();
  const markerRef = useRef<google.maps.marker.AdvancedMarkerElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!map || !containerRef.current) return;

    const marker = new google.maps.marker.AdvancedMarkerElement({
      map,
      position,
      title,
      content: content ? containerRef.current : undefined,
    });

    if (onClick) {
      marker.addListener('click', onClick);
    }

    markerRef.current = marker;

    return () => {
      marker.map = null;
      markerRef.current = null;
    };
  }, [map, position.lat, position.lng, title, onClick, content]);

  return <div ref={containerRef} style={{ display: content ? 'contents' : 'none' }} />;
}
