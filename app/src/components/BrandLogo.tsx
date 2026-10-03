import { publicUrl } from '../lib/publicUrl';

/** Original supplied artwork: preserve its proportions and dark background. */
export default function BrandLogo({ footer = false }: { footer?: boolean }) {
  return <span className="inline-flex shrink-0 overflow-hidden rounded-lg bg-black">
    <img src={publicUrl('brand/dhofar-academia.jpg')} alt="Dhofar Academia"
      width={1536} height={496} loading={footer ? 'lazy' : 'eager'}
      className={footer ? 'h-auto w-40' : 'h-auto w-28 sm:w-40'} />
  </span>;
}
