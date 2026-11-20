async function toBlob(photo) {
  if (photo?.file) return photo.file
  const src = photo?.base64 || photo?.url
  if (!src) return null
  const r = await fetch(src, { mode: 'cors' })      // data:, blob:, or CORS-enabled http(s)
  if (!r.ok) throw new Error('Could not read the photo')
  return await r.blob()
}
// The ONLY place a photo is resized for AI. EXIF orientation is baked in; the returned dataUrl is
// the exact pixel grid the backend renders on AND the exact "Before" image shown in the slider.
export async function preparePhotoForAI(photo, longSide = 1536, quality = 0.92) {
  const blob = await toBlob(photo)
  if (!blob) return null
  const bmp = await createImageBitmap(blob, { imageOrientation: 'from-image' })
  const s = Math.min(1, longSide / Math.max(bmp.width, bmp.height))
  const width = Math.round(bmp.width * s), height = Math.round(bmp.height * s)
  const c = document.createElement('canvas'); c.width = width; c.height = height
  const ctx = c.getContext('2d')
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, width, height)       // PNG transparency -> white, not black
  ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high'
  ctx.drawImage(bmp, 0, 0, width, height); bmp.close?.()
  return { dataUrl: c.toDataURL('image/jpeg', quality), width, height }
}
