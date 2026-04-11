// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "xReaderCheck",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "xReaderCheck",
            path: "CheckSources",
            sources: [
                "Models", "NetworkStub"
            ]
        )
    ]
)
