/**
 * The painted layer stack behind (and in front of) the action.
 *
 * Each layer scrolls at its own rate: 1.0 moves with the world, lower values
 * sit further away, and values above 1.0 sit in front of the player. A layer
 * flagged `overPlayer` is drawn after entities, which is what puts a doorframe
 * or a foreground pillar between the camera and the character.
 */
export class Backdrop {
  constructor(layers, assets) {
    this.layers = layers.map((layer) => ({
      parallax: layer.parallax === undefined ? 1 : layer.parallax,
      parallaxY: layer.parallaxY === undefined ? layer.parallax === undefined ? 1 : layer.parallax : layer.parallaxY,
      overPlayer: !!layer.overPlayer,
      repeat: !!layer.repeat,
      offsetX: layer.offsetX || 0,
      offsetY: layer.offsetY || 0,
      alpha: layer.alpha === undefined ? 1 : layer.alpha,
      image: assets.image(layer.image),
      path: layer.image,
    }));
  }

  drawBehind(ctx, camera) {
    this._draw(ctx, camera, false);
  }

  drawFront(ctx, camera) {
    this._draw(ctx, camera, true);
  }

  _draw(ctx, camera, over) {
    for (const layer of this.layers) {
      if (layer.overPlayer !== over) continue;
      const x = Math.round(-camera.drawX * layer.parallax + layer.offsetX);
      const y = Math.round(-camera.drawY * layer.parallaxY + layer.offsetY);

      const prev = ctx.globalAlpha;
      if (layer.alpha !== 1) ctx.globalAlpha = prev * layer.alpha;

      if (layer.repeat) {
        // Tile horizontally so a narrow far layer can cover a wide scene.
        const w = layer.image.width;
        let start = x % w;
        if (start > 0) start -= w;
        for (let dx = start; dx < ctx.canvas.width; dx += w) {
          ctx.drawImage(layer.image, dx, y);
        }
      } else {
        ctx.drawImage(layer.image, x, y);
      }

      if (layer.alpha !== 1) ctx.globalAlpha = prev;
    }
  }

  /** Every image path the stack needs, for the asset manifest. */
  static paths(layers) {
    return layers.map((l) => l.image);
  }
}
