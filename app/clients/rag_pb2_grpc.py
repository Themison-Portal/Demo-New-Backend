"""
Generated gRPC stubs for RAG service.
This file is a placeholder - generate actual code using:
  python -m grpc_tools.protoc -I../rag-service/protos --python_out=. --grpc_python_out=. rag/v1/rag_service.proto
"""
import grpc

from app.clients import rag_pb2 as pb2


class RagServiceStub:
    """
    gRPC stub for RagService.
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.IngestPdf = channel.unary_stream(
            '/themison.rag.v1.RagService/IngestPdf',
            request_serializer=self._serialize_ingest_pdf_request,
            response_deserializer=self._deserialize_ingest_pdf_progress,
        )
        self.Query = channel.unary_unary(
            '/themison.rag.v1.RagService/Query',
            request_serializer=self._serialize_query_request,
            response_deserializer=self._deserialize_query_response,
        )
        self.GetHighlightedPdf = channel.unary_unary(
            '/themison.rag.v1.RagService/GetHighlightedPdf',
            request_serializer=self._serialize_highlighted_pdf_request,
            response_deserializer=self._deserialize_highlighted_pdf_response,
        )
        self.InvalidateDocument = channel.unary_unary(
            '/themison.rag.v1.RagService/InvalidateDocument',
            request_serializer=self._serialize_invalidate_request,
            response_deserializer=self._deserialize_invalidate_response,
        )
        self.HealthCheck = channel.unary_unary(
            '/themison.rag.v1.RagService/HealthCheck',
            request_serializer=self._serialize_health_check_request,
            response_deserializer=self._deserialize_health_check_response,
        )

    @staticmethod
    def _serialize_ingest_pdf_request(request):
        """Serialize IngestPdfRequest."""
        # This is a placeholder - actual implementation would use protobuf serialization
        import json
        return json.dumps({
            'document_url': request.document_url,
            'document_id': request.document_id,
            'chunk_size': request.chunk_size,
        }).encode()

    @staticmethod
    def _deserialize_ingest_pdf_progress(data):
        """Deserialize IngestPdfProgress."""
        import json
        d = json.loads(data.decode())
        result = None
        if d.get('result'):
            result = pb2.IngestResult(**d['result'])
        return pb2.IngestPdfProgress(
            stage=d.get('stage', 0),
            progress_percent=d.get('progress_percent', 0),
            message=d.get('message', ''),
            result=result,
        )

    @staticmethod
    def _serialize_query_request(request):
        """Serialize QueryRequest."""
        import json
        return json.dumps({
            'query': request.query,
            'document_id': request.document_id,
            'document_name': request.document_name,
            'top_k': request.top_k,
            'min_score': request.min_score,
        }).encode()

    @staticmethod
    def _deserialize_query_response(data):
        """Deserialize QueryResponse."""
        import json
        d = json.loads(data.decode())

        # Parse sources
        sources = []
        for s in d.get('answer', {}).get('sources', []):
            bboxes = [pb2.BBox(**b) for b in s.get('bboxes', [])]
            sources.append(pb2.RagSource(
                name=s.get('name', ''),
                page=s.get('page', 0),
                section=s.get('section', ''),
                exact_text=s.get('exact_text', ''),
                bboxes=bboxes,
                relevance=s.get('relevance', pb2.RELEVANCE_HIGH),
            ))

        answer = pb2.RagAnswer(
            response=d.get('answer', {}).get('response', ''),
            sources=sources,
        )
        timing = pb2.QueryTiming(**d.get('timing', {}))
        cache_info = pb2.CacheInfo(**d.get('cache_info', {}))

        return pb2.QueryResponse(answer=answer, timing=timing, cache_info=cache_info)

    @staticmethod
    def _serialize_highlighted_pdf_request(request):
        """Serialize GetHighlightedPdfRequest."""
        import json
        bboxes = [{'x0': b.x0, 'y0': b.y0, 'x1': b.x1, 'y1': b.y1} for b in request.bboxes]
        return json.dumps({
            'document_url': request.document_url,
            'page': request.page,
            'bboxes': bboxes,
        }).encode()

    @staticmethod
    def _deserialize_highlighted_pdf_response(data):
        """Deserialize HighlightedPdfResponse."""
        # For binary data, we handle differently
        return pb2.HighlightedPdfResponse(
            pdf_content=data,
            content_type='application/pdf',
        )

    @staticmethod
    def _serialize_invalidate_request(request):
        """Serialize InvalidateDocumentRequest."""
        import json
        return json.dumps({'document_id': request.document_id}).encode()

    @staticmethod
    def _deserialize_invalidate_response(data):
        """Deserialize InvalidateDocumentResponse."""
        import json
        d = json.loads(data.decode())
        return pb2.InvalidateDocumentResponse(**d)

    @staticmethod
    def _serialize_health_check_request(request):
        """Serialize HealthCheckRequest."""
        return b'{}'

    @staticmethod
    def _deserialize_health_check_response(data):
        """Deserialize HealthCheckResponse."""
        import json
        d = json.loads(data.decode())
        components = [pb2.ComponentHealth(**c) for c in d.get('components', [])]
        return pb2.HealthCheckResponse(
            status=d.get('status', 0),
            version=d.get('version', ''),
            components=components,
        )


class RagServiceServicer:
    """
    Service interface for RagService (server-side).
    """

    async def IngestPdf(self, request, context):
        """Ingest PDF with streaming progress."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    async def Query(self, request, context):
        """RAG query."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    async def GetHighlightedPdf(self, request, context):
        """Get highlighted PDF."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    async def InvalidateDocument(self, request, context):
        """Invalidate document cache."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    async def HealthCheck(self, request, context):
        """Health check."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_RagServiceServicer_to_server(servicer, server):
    """Add RagServiceServicer to server."""
    rpc_method_handlers = {
        'IngestPdf': grpc.unary_stream_rpc_method_handler(
            servicer.IngestPdf,
        ),
        'Query': grpc.unary_unary_rpc_method_handler(
            servicer.Query,
        ),
        'GetHighlightedPdf': grpc.unary_unary_rpc_method_handler(
            servicer.GetHighlightedPdf,
        ),
        'InvalidateDocument': grpc.unary_unary_rpc_method_handler(
            servicer.InvalidateDocument,
        ),
        'HealthCheck': grpc.unary_unary_rpc_method_handler(
            servicer.HealthCheck,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        'themison.rag.v1.RagService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
