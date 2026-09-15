import type { JSX } from "react";
interface CharactersProps {
  className?: string;
  priority?: boolean;
}

const imageList = [
  {
    src: "/images/ganadi-img.png",
    alt: "가나디",
  },
  {
    src: "/images/usagi-img.jpg",
    alt: "우사기",
  },
  {
    src: "/images/heachi-img.jpeg",
    alt: "해치",
  },
] as const;

function Characters({
  className = "",
  priority = false,
}: CharactersProps): JSX.Element {
  const containerClassName = ["mascots", className]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={containerClassName} aria-label="캐릭터 소개">
      {imageList.map((image, index) => (
        <img
          className={`mascot mascot-${index + 1}`}
          key={image.src}
          src={image.src}
          alt={image.alt}
          width={120}
          height={145}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
        />
      ))}
    </div>
  );
}

export default Characters;
