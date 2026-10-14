#!/usr/bin/env python3
"""Preserve the ancestor and composite only image-tool pigment on vacant rock."""
import hashlib
import json
from pathlib import Path
from image_bytes import read_png, png, jpeg, resize

ANCESTOR = '36db5a46fd1287c78802711d85ae0ad37ff3ef63f61523e2c96c413c6534c8d4'
PROMPT = ('A single small prehistoric ochre pouch enclosing a round red ochre pebble, '
          'rough charcoal outline and tied neck, warm rough torchlit stone, worn earthy '
          'pigment. No hands, figures, writing, numbers, logos, watermark or borders.')


def main():
    folder = Path('artifacts/line-4')
    before = (folder / 'wall.png').read_bytes()
    assert hashlib.sha256(before).hexdigest() == ANCESTOR
    draft = (folder / 'wall-v6.png').read_bytes()
    w, h, old = read_png(before)
    gw, gh, generated = read_png(draft)
    assert (w, h) == (1254, 1254)
    assert (gw, gh) == (1024, 1024)
    final = bytearray(old)
    changed = 0
    bounds = [w, h, 0, 0]
    for y in range(830, 995):
        for x in range(105, 260):
            sx = 260 + (x - 105) * 500 // 155
            sy = 140 + (y - 830) * 710 // 165
            body = ((sx - 500) / 235)**2 + ((sy - 580) / 250)**2 < 1
            neck = 365 < sx < 655 and 160 < sy < 375
            tie = 535 < sx < 720 and 315 < sy < 505
            if not (body or neck or tie):
                continue
            i, j = (y*w+x)*3, (sy*gw+sx)*3
            r, g, b = generated[j:j+3]
            # Preserve deep inherited fissures inside the otherwise vacant area.
            if sum(old[i:i+3]) < 160:
                continue
            charcoal = r < 80 and g < 65 and b < 55
            red = r > 85 and g < r*.53 and b < r*.35
            yellow = body and r > 125 and g > 65 and g < r*.76 and b < g*.5
            if not (charcoal or red or yellow):
                continue
            opacity = .62 if charcoal else .43
            final[i:i+3] = bytes(round(a*(1-opacity)+v*opacity)
                                 for a, v in zip(old[i:i+3], (r, g, b)))
            if final[i:i+3] != old[i:i+3]:
                changed += 1
                bounds = [min(bounds[0], x), min(bounds[1], y),
                          max(bounds[2], x), max(bounds[3], y)]
    assert changed > 1000
    output = png(w, h, final)
    for name in ('wall.png', 'wall-v6.png'):
        (folder / name).write_bytes(output)
    preview = jpeg(512, 512, resize(w, h, final), 52)
    assert len(preview) < 100000
    Path('dist/line-4/26.jpg').write_bytes(preview)
    review = {
        'wall': {'paths': ['artifacts/line-4/wall.png', 'artifacts/line-4/wall-v6.png'],
                 'width': w, 'height': h, 'format': 'PNG', 'mode': 'RGB',
                 'sha256': hashlib.sha256(output).hexdigest()},
        'preview': {'path': 'dist/line-4/26.jpg', 'width': 512, 'height': 512,
                    'format': 'JPEG', 'bytes': len(preview)},
        'ancestorSha256': ANCESTOR, 'generatedImageSha256': hashlib.sha256(draft).hexdigest(),
        'changedPixels': changed, 'unchangedPixels': w*h-changed,
        'additionBounds': bounds,
        'preservation': 'Only generated pigment on vacant lower-left rock. All pixels outside the addition, including every ancestor mark and Pepe, are identical. Deep cracks inside the addition are retained.',
        'imageTool': 'installed image generate_image', 'prompt': PROMPT,
        'visualReview': 'Pending inspection', 'unmetVisualRequirements': [],
        'limitations': ['Local visual review is not independent certification.',
                        'The small worn motif is subtler in the 512-pixel preview.']}
    Path('line-4/wall-review-26.json').write_text(json.dumps(review, indent=2)+'\n')
    record = {'name': 'The Enclosed Message',
              'image': 'https://api.imd.fun/artifacts/'+review['wall']['sha256'],
              'attributes': [
                  {'trait_type': 'Cave', 'value': 'Water'},
                  {'trait_type': 'Wall', 'value': 'Line 4'},
                  {'trait_type': 'Number', 'value': 26},
                  {'trait_type': 'Left behind', 'value': 'offline captured EIP-712 request checker'},
                  {'trait_type': 'Meaning', 'value': 'Pepe checks the message and the pouch that carries it.'},
                  {'trait_type': 'One thing', 'value': 'offline EIP-712 typed-data digest checking'}]}
    Path('dist/line-4/26.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(review, indent=2))


if __name__ == '__main__':
    main()
