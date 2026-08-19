export function HerculesLogo({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Outer hexagonal frame */}
      <path
        d="M60 10 L95 30 L95 70 L60 90 L25 70 L25 30 Z"
        stroke="#ffffff"
        strokeWidth="2"
        fill="none"
        opacity="0.8"
      />
      
      {/* Inner hexagonal structure */}
      <g transform="translate(60,60)">
        {/* Central hexagonal core */}
        <path
          d="M0,-15 L13,-7.5 L13,7.5 L0,15 L-13,7.5 L-13,-7.5 Z"
          fill="#ffffff"
          opacity="0.9"
        />
        
        {/* Geometric pattern elements */}
        <path
          d="M-25,-15 L-13,-7.5 L-25,0 L-13,7.5 L-25,15"
          stroke="#ffffff"
          strokeWidth="1.5"
          fill="none"
          opacity="0.7"
        />
        
        <path
          d="M25,-15 L13,-7.5 L25,0 L13,7.5 L25,15"
          stroke="#ffffff"
          strokeWidth="1.5"
          fill="none"
          opacity="0.7"
        />
        
        {/* Top and bottom connecting lines */}
        <path
          d="M-13,-7.5 L0,-15 L13,-7.5"
          stroke="#ffffff"
          strokeWidth="1.5"
          fill="none"
          opacity="0.7"
        />
        
        <path
          d="M-13,7.5 L0,15 L13,7.5"
          stroke="#ffffff"
          strokeWidth="1.5"
          fill="none"
          opacity="0.7"
        />
        
        {/* Corner accent dots */}
        <circle cx="-20" cy="-12" r="1.5" fill="#ffffff" opacity="0.8" />
        <circle cx="20" cy="-12" r="1.5" fill="#ffffff" opacity="0.8" />
        <circle cx="-20" cy="12" r="1.5" fill="#ffffff" opacity="0.8" />
        <circle cx="20" cy="12" r="1.5" fill="#ffffff" opacity="0.8" />
      </g>
    </svg>
  );
}

export function HerculesTextLogo({ className = "h-8" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 280 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Complete Hercules logo with text */}
      <g>
        {/* Hexagonal logo on the left */}
        <g transform="translate(20,40)">
          {/* Outer hexagonal frame */}
          <path
            d="M0,-15 L13,-7.5 L13,7.5 L0,15 L-13,7.5 L-13,-7.5 Z"
            stroke="#ffffff"
            strokeWidth="1.5"
            fill="none"
            opacity="0.9"
          />
          
          {/* Inner geometric pattern */}
          <path
            d="M-8,-5 L0,-8 L8,-5 L8,5 L0,8 L-8,5 Z"
            fill="#ffffff"
            opacity="0.8"
          />
          
          {/* Side connecting elements */}
          <path
            d="M-13,-3 L-8,-5 M-13,3 L-8,5 M13,-3 L8,-5 M13,3 L8,5"
            stroke="#ffffff"
            strokeWidth="1"
            opacity="0.7"
          />
        </g>
        
        {/* HERCULES text */}
        <g transform="translate(55,25)">
          <text
            x="0"
            y="20"
            fill="#ffffff"
            fontSize="24"
            fontFamily="Arial, sans-serif"
            fontWeight="bold"
            letterSpacing="1px"
          >
            HERCULES
          </text>
          
          {/* v2.0 version */}
          <text
            x="0"
            y="40"
            fill="#ffffff"
            fontSize="12"
            fontFamily="Arial, sans-serif"
            fontWeight="normal"
            letterSpacing="0.5px"
            opacity="0.8"
          >
            v2.0
          </text>
          
          {/* Underline */}
          <line
            x1="0"
            y1="45"
            x2="80"
            y2="45"
            stroke="#ffffff"
            strokeWidth="1"
            opacity="0.6"
          />
        </g>
      </g>
    </svg>
  );
}