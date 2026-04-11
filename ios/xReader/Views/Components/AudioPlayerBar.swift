import SwiftUI

struct AudioPlayerBar: View {
    let player: AudioPlayerService

    var body: some View {
        VStack(spacing: 0) {
            Divider()
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(player.currentTitle)
                        .font(.subheadline)
                        .lineLimit(1)
                    Text(player.currentBookTitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                Spacer()

                Button { player.togglePlayPause() } label: {
                    Image(systemName: player.isPlaying ? "pause.circle.fill" : "play.circle.fill")
                        .font(.title)
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 10)

            if player.duration > 0 {
                ProgressView(value: player.currentTime, total: player.duration)
                    .tint(.blue)
            }
        }
        .background(.bar)
    }
}
