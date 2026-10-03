import { publicUrl } from '../lib/publicUrl';

/** Screen blending maps the artwork's black background to the interface green. */
export default function BrandLogo({ footer = false }: { footer?: boolean }) {
  return <span className="isolate inline-flex shrink-0 overflow-hidden rounded-lg bg-crop-700">
    <img src={publicUrl('brand/dhofar-academia.jpg')} alt="Dhofar Academia"
      width={1536} height={496} loading={footer ? 'lazy' : 'eager'}
      className={`mix-blend-screen ${footer ? 'h-auto w-40' : 'h-auto w-28 sm:w-40'}`} />
  </span>;
}
